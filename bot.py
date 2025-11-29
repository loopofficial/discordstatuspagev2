import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import discord
from discord.ext import tasks, commands

from config import Config
from models import ServiceStateManager, ServiceStatus
from monitor import ServiceMonitor, CheckResult

logger = logging.getLogger(__name__)

class IncidentView(discord.ui.View):
    def __init__(self, bot: "ServiceMonitorBot", service_name: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.service_name = service_name

    @discord.ui.button(label="Clear Incident", style=discord.ButtonStyle.danger)
    async def clear_incident(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.bot.clear_incident(self.service_name, interaction)

class ServiceMonitorBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self.config = config
        self.state_manager = ServiceStateManager()
        self.monitor = ServiceMonitor(
            ping_attempts=config.monitoring.ping_attempts,
            ping_delay=config.monitoring.ping_delay,
            http_timeout=config.monitoring.http_timeout
        )

        self._live_message_id: Optional[int] = None
        self._active_incidents: Dict[str, int] = {}

        all_services = (
            config.services.websites +
            list(config.services.servers.keys())
        )
        self.state_manager.initialize(all_services)

    async def setup_hook(self) -> None:
        logger.info("Bot is initializing...")

    async def on_ready(self) -> None:
        logger.info(f"Connected as {self.user.name} (ID: {self.user.id})")
        logger.info(f"Monitoring {len(self.config.services.websites)} websites and {len(self.config.services.servers)} servers")
        if not self.update_loop.is_running():
            self.update_loop.start()

    @tasks.loop(seconds=10)
    async def update_loop(self) -> None:
        try:
            await self._run_monitoring_cycle()
            await self._update_dashboard()
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

    @update_loop.before_loop
    async def before_update_loop(self) -> None:
        await self.wait_until_ready()
        try:
            self.update_loop.change_interval(seconds=self.config.monitoring.update_interval)
        except Exception:
            logger.warning("Could not adjust monitoring interval; using default")

    async def _run_monitoring_cycle(self) -> None:
        results = await self.monitor.check_all(
            self.config.services.websites,
            self.config.services.servers
        )

        newly_down: List[str] = []
        restored: List[Tuple[str, timedelta]] = []

        for result in results:
            state = self.state_manager.get(result.service_name)
            if result.is_up:
                state.reset_failure_count()
                if state.status == ServiceStatus.DOWN:
                    down_duration = datetime.now() - state.down_since
                    state.mark_up(result.latency)
                    restored.append((result.service_name, down_duration))
                else:
                    state.latency = result.latency
                    if result.latency:
                        threshold = self.config.services.latency_thresholds.get(
                            result.service_name,
                            self.config.monitoring.default_latency_threshold
                        )
                        if result.latency > threshold:
                            await self._handle_slow_response(result.service_name, result.latency)
            else:
                state.increment_failure()
                if (state.failure_count >= self.config.monitoring.failure_threshold
                        and state.status == ServiceStatus.UP):
                    state.mark_down()
                    newly_down.append(result.service_name)

        if newly_down:
            await self._create_incident(newly_down)
            await self._notify_role(newly_down)
        for service_name, duration in restored:
            await self._update_incident_restored(service_name, duration)

    async def _handle_slow_response(self, service_name: str, latency: float) -> None:
        state = self.state_manager.get(service_name)
        cooldown = timedelta(minutes=self.config.monitoring.slow_alert_cooldown_minutes)
        if (not state.last_slow_alert or datetime.now() - state.last_slow_alert > cooldown):
            state.last_slow_alert = datetime.now()
            logger.warning(f"High latency detected for {service_name}: {latency}ms")

    async def _update_dashboard(self) -> None:
        channel = self.get_channel(self.config.discord.channel_id)
        if not channel:
            logger.error("Status channel not found")
            return
        embed = self._build_dashboard_embed()
        try:
            if self._live_message_id:
                message = await channel.fetch_message(self._live_message_id)
                await message.edit(embed=embed)
            else:
                message = await channel.send(embed=embed)
                self._live_message_id = message.id
        except discord.NotFound:
            message = await channel.send(embed=embed)
            self._live_message_id = message.id
        except discord.HTTPException as e:
            logger.error(f"Failed to update dashboard: {e}")

    def _build_dashboard_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Service Status Dashboard",
            description="Real-time monitoring status for all services.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        categories = self._get_service_categories()
        for category, services in categories.items():
            lines = []
            for service in services:
                state = self.state_manager.get(service)
                status_icon = "🟢" if state.status == ServiceStatus.UP else "🔴"
                line = f"{status_icon} {service}: **{state.status.value}**"
                if state.latency is not None:
                    line += f" - {state.latency}ms"
                if state.status == ServiceStatus.DOWN and state.down_since:
                    downtime = state.get_downtime()
                    line += f" - Down for {downtime}"
                lines.append(line)
            if lines:
                embed.add_field(name=category, value="\n".join(lines), inline=False)
        return embed

    def _get_service_categories(self) -> Dict[str, List[str]]:
        if self.config.services.service_categories:
            return self.config.services.service_categories
        categories = {}
        if self.config.services.websites:
            categories["Websites"] = self.config.services.websites
        if self.config.services.servers:
            categories["Servers"] = list(self.config.services.servers.keys())
        return categories

    async def _create_incident(self, down_services: List[str]) -> None:
        channel = self.get_channel(self.config.discord.alert_channel_id)
        if not channel:
            logger.error("Alert channel not found")
            return
        if not self._active_incidents:
            embed = discord.Embed(
                title="Incident Report",
                description=f"{len(down_services)} service{'s' if len(down_services) > 1 else ''} experiencing issues.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            for service in down_services:
                embed.add_field(name=service, value="Service Down", inline=False)
            message = await channel.send(embed=embed)
            for service in down_services:
                self._active_incidents[service] = message.id
                self.state_manager.get(service).incident_message_id = message.id
            await self._send_alert_ping(channel)
        else:
            message_id = next(iter(self._active_incidents.values()))
            try:
                message = await channel.fetch_message(message_id)
                embed = message.embeds[0]
                for service in down_services:
                    if service not in self._active_incidents:
                        embed.add_field(name=service, value="Service Down", inline=False)
                        self._active_incidents[service] = message_id
                        self.state_manager.get(service).incident_message_id = message_id
                await message.edit(embed=embed)
            except discord.NotFound:
                logger.warning("Incident message not found, clearing incidents")
                self._active_incidents.clear()

    async def _update_incident_restored(self, service_name: str, duration: timedelta) -> None:
        message_id = self._active_incidents.get(service_name)
        if not message_id:
            return
        channel = self.get_channel(self.config.discord.alert_channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            duration_str = str(duration).split('.')[0]
            for i, field in enumerate(embed.fields):
                if field.name == service_name:
                    embed.set_field_at(i, name=service_name, value=f"Restored - Downtime: {duration_str}", inline=False)
                    break
            view = IncidentView(self, service_name)
            await message.edit(embed=embed, view=view)
        except discord.NotFound:
            self._active_incidents.pop(service_name, None)

    async def clear_incident(self, service_name: str, interaction: discord.Interaction) -> None:
        message_id = self._active_incidents.get(service_name)
        if not message_id:
            await interaction.response.defer()
            return
        try:
            channel = self.get_channel(self.config.discord.alert_channel_id)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            embed.clear_fields()
            remaining = False
            for name, state in self.state_manager:
                if state.status == ServiceStatus.DOWN:
                    downtime = state.get_downtime() or "Unknown"
                    embed.add_field(name=name, value=f"Service Down - Downtime: {downtime}", inline=False)
                    remaining = True
            if remaining:
                await message.edit(embed=embed)
            else:
                await message.delete()
                self._active_incidents.clear()
            self._active_incidents.pop(service_name, None)
            self.state_manager.get(service_name).incident_message_id = None
            await interaction.response.defer()
        except discord.NotFound:
            await interaction.response.defer()

    async def _send_alert_ping(self, channel) -> None:
        try:
            notification = await channel.send("@everyone")
            await notification.delete()
        except discord.HTTPException:
            pass

    async def _notify_role(self, down_services: List[str]) -> None:
        if not self.config.discord.alert_role_name:
            return
        channel = self.get_channel(self.config.discord.alert_channel_id)
        if not channel or not hasattr(channel, 'guild'):
            return
        guild = channel.guild
        role = discord.utils.get(guild.roles, name=self.config.discord.alert_role_name)
        if not role:
            logger.warning(f"Alert role '{self.config.discord.alert_role_name}' not found")
            return
        service_list = ", ".join(down_services)
        plural = "s are" if len(down_services) > 1 else " is"
        message = f"The following service{plural} experiencing issues: {service_list}"
        sent = 0
        failed = 0
        for member in role.members:
            if getattr(member, "bot", False):
                continue
            try:
                await member.send(message)
                sent += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1
                continue
            except Exception:
                failed += 1
                continue
        if failed:
            logger.info(f"Alert DMs sent: {sent}, failed: {failed} (DMs disabled or bots)")

    @commands.command(name="status")
    async def status_command(self, ctx: commands.Context) -> None:
        try:
            embed = self._build_dashboard_embed()
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("Unable to build status right now.")
            logger.error(f"Status command failed: {e}")


def create_bot(config: Config) -> ServiceMonitorBot:
    return ServiceMonitorBot(config)
