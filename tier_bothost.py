import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import os
import sys
from datetime import datetime

print("🚀 Запуск бота на Railway...")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORY_ID = 1381679976486539334
LOG_CHANNEL_ID = 1448991378750046209
ALLOWED_ROLE_IDS = [1310673963000528949, 1381682246678741022, 1223589384452833290]  # Роли с доступом к командам
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("❌ ОШИБКА: DISCORD_TOKEN не найден!")
    sys.exit(1)

print("✅ Токен найден, запускаем бота...")

async def send_log(action: str, user: discord.User, details: str = "", fields: list = None):
    """Отправляет лог в канал логов"""
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title=f"📝 {action}",
                color=0x3498db if "✅" in action else (0x00ff00 if "📋" in action else 0xff0000),
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Пользователь", value=f"{user.mention} ({user.id})", inline=False)
            
            if fields:
                for name, value in fields:
                    embed.add_field(name=name, value=value[:1024] if value else "Не указано", inline=False)
            
            if details:
                embed.add_field(name="📋 Детали", value=details[:1024] if details else "Нет деталей", inline=False)
            
            embed.set_footer(text=f"ID: {user.id} • {datetime.now().strftime('%H:%M:%S')}")
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке лога: {e}")

def has_allowed_role():
    """Декоратор для проверки наличия разрешенных ролей"""
    async def predicate(interaction: discord.Interaction) -> bool:
        # Проверяем, есть ли у пользователя хотя бы одна из разрешенных ролей
        user_roles = [role.id for role in interaction.user.roles]
        has_role = any(role_id in user_roles for role_id in ALLOWED_ROLE_IDS)
        
        # Также разрешаем администраторам и модераторам
        if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_messages:
            return True
            
        return has_role
    
    return app_commands.check(predicate)

class TierApplication(ui.Modal, title='Заявка на Tier'):
    def __init__(self):
        super().__init__()
        self.nickname_value = ""
        self.screenshots_value = ""
        self.arena_videos_value = ""
        self.capt_videos_value = ""
        self.rp_mcl_videos_value = ""
    
    nickname = ui.TextInput(
        label='Никнейм | Статик ID',
        placeholder='Пример: Skeet Amnyam | 2253',
        max_length=50
    )
    
    screenshots = ui.TextInput(
        label='10 скринов с 50+ киллов',
        placeholder='Ссылки на imgur/ibb (через запятую)',
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    arena_videos = ui.TextInput(
        label='2 видео с арены (тяжка/спешик + сайга)',
        placeholder='Ссылки на 2 полных 10-минутных видео',
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    capt_videos = ui.TextInput(
        label='Видео залазы',
        placeholder='Ссылки на видео',
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    rp_mcl_videos = ui.TextInput(
        label='Капты откаты + MCL (по желанию)',
        placeholder='Сначала капты откаты, затем MCL если есть',
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Сохраняем значения
            self.nickname_value = self.nickname.value
            self.screenshots_value = self.screenshots.value
            self.arena_videos_value = self.arena_videos.value
            self.capt_videos_value = self.capt_videos.value
            self.rp_mcl_videos_value = self.rp_mcl_videos.value
            
            category = bot.get_channel(CATEGORY_ID)
            if not category:
                await interaction.followup.send('❌ Ошибка: не найдена категория для заявок', ephemeral=True)
                return

            channel_name = f"tier-{interaction.user.display_name}"[:100]
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Добавляем права для администраторов и модераторов
            for role in interaction.guild.roles:
                if role.permissions.administrator or role.permissions.manage_messages:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            channel = await category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Заявка на Tier от {interaction.user.display_name}"
            )
            
            embed = discord.Embed(
                title=f"🎯 Заявка на Tier от {interaction.user.display_name}",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="👤 Игрок", value=f"```{self.nickname_value}```", inline=False)
            embed.add_field(name="📸 10 скринов с 50+ киллов", value=f"{self.screenshots_value[:500]}..." if len(self.screenshots_value) > 500 else self.screenshots_value, inline=False)
            embed.add_field(name="🎮 2 видео с арены", value=f"{self.arena_videos_value[:500]}..." if len(self.arena_videos_value) > 500 else self.arena_videos_value, inline=False)
            embed.add_field(name="⚔️ Видео залазы", value=f"{self.capt_videos_value[:500]}..." if len(self.capt_videos_value) > 500 else self.capt_videos_value, inline=False)
            embed.add_field(name="🎭 капты + MCL откаты", value=f"{self.rp_mcl_videos_value[:500]}..." if len(self.rp_mcl_videos_value) > 500 else self.rp_mcl_videos_value, inline=False)
            embed.set_footer(text=f"ID пользователя: {interaction.user.id}")
            
            view = ModerationView(
                applicant_id=interaction.user.id,
                channel_id=channel.id,
                nickname=self.nickname_value,
                screenshots=self.screenshots_value,
                arena_videos=self.arena_videos_value,
                capt_videos=self.capt_videos_value,
                rp_mcl_videos=self.rp_mcl_videos_value
            )
            
            await channel.send(embed=embed, view=view)
            await channel.send(f"👤 Заявитель: {interaction.user.mention}")
            
            await interaction.followup.send(f'✅ Ваша заявка создана! Перейдите в {channel.mention}', ephemeral=True)
            
            # Логируем создание заявки со всеми ссылками
            log_fields = [
                ("🎯 Никнейм", f"`{self.nickname_value}`"),
                ("📸 Скрины (50+ киллов)", self.screenshots_value[:800] if self.screenshots_value else "Не указано"),
                ("🎮 Видео арены", self.arena_videos_value[:800] if self.arena_videos_value else "Не указано"),
                ("⚔️ Видео залазы", self.capt_videos_value[:800] if self.capt_videos_value else "Не указано"),
                ("🎭 капты + MCL откаты", self.rp_mcl_videos_value[:800] if self.rp_mcl_videos_value else "Не указано"),
                ("#️⃣ Канал", f"{channel.mention} (`{channel.id}`)")
            ]
            
            await send_log(
                "✅ Новая заявка на Tier",
                interaction.user,
                f"Канал создан: {channel.mention}",
                fields=log_fields
            )
            
        except Exception as e:
            print(f"Ошибка при создании заявки: {e}")
            try:
                await interaction.followup.send('❌ Ошибка при создании заявки.', ephemeral=True)
            except:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Ошибка в модальном окне: {error}")
        try:
            await interaction.response.send_message('❌ Ошибка при отправке заявки.', ephemeral=True)
        except:
            try:
                await interaction.followup.send('❌ Ошибка при отправке заявки.', ephemeral=True)
            except:
                pass

class ModerationView(discord.ui.View):
    def __init__(self, applicant_id, channel_id, nickname, screenshots, arena_videos, capt_videos, rp_mcl_videos):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.channel_id = channel_id
        self.nickname = nickname
        self.screenshots = screenshots
        self.arena_videos = arena_videos
        self.capt_videos = capt_videos
        self.rp_mcl_videos = rp_mcl_videos
        self.taken = False
        self.closed_by = None
    
    @discord.ui.button(label="✅ Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_review")
    async def take_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.taken:
            await interaction.response.defer()
            return
        
        self.taken = True
        button.disabled = True
        button.label = "✅ На рассмотрении"
        await interaction.message.edit(view=self)
        await interaction.channel.send(f"📋 **Заявка взята на рассмотрение** {interaction.user.mention}")
        await interaction.response.defer()
        
        # Логируем взятие на рассмотрение
        log_fields = [
            ("👤 Заявитель", f"<@{self.applicant_id}>"),
            ("🎯 Никнейм", f"`{self.nickname}`"),
            ("📋 Взял на рассмотрение", f"{interaction.user.mention}"),
            ("#️⃣ Канал", f"<#{self.channel_id}>")
        ]
        
        await send_log(
            "📋 Заявка взята на рассмотрение",
            interaction.user,
            f"Модератор: {interaction.user.mention}",
            fields=log_fields
        )
    
    @discord.ui.button(label="❌ Закрыть заявку", style=discord.ButtonStyle.danger, custom_id="close_application")
    async def close_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверяем права через декоратор
        user_roles = [role.id for role in interaction.user.roles]
        has_allowed = any(role_id in user_roles for role_id in ALLOWED_ROLE_IDS)
        has_perms = interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_messages
        
        if not has_allowed and not has_perms:
            await interaction.response.send_message("❌ У вас нет прав для закрытия заявок.", ephemeral=True)
            return
        
        channel = interaction.channel
        self.closed_by = interaction.user
        
        # Логируем закрытие заявки со всеми данными
        log_fields = [
            ("🔒 Закрыл", f"{interaction.user.mention} ({interaction.user.id})"),
            ("👤 Заявитель", f"<@{self.applicant_id}>"),
            ("🎯 Никнейм", f"`{self.nickname}`"),
            ("📸 Скрины", self.screenshots[:800] if self.screenshots else "Не указано"),
            ("🎮 Видео арены", self.arena_videos[:800] if self.arena_videos else "Не указано"),
            ("⚔️ Видео залазов", self.capt_videos[:800] if self.capt_videos else "Не указано"),
            ("🎭 Капты + MCL", self.rp_mcl_videos[:800] if self.rp_mcl_videos else "Не указано"),
            ("#️⃣ Канал", f"#{channel.name} (`{channel.id}`)")
        ]
        
        await send_log(
            "🔒 Заявка закрыта",
            interaction.user,
            f"Модератор: {interaction.user.mention} закрыл заявку",
            fields=log_fields
        )
        
        await interaction.channel.send(f"🔒 **Заявка закрыта** {interaction.user.mention}\nКанал удалится через 5 секунд...")
        await interaction.response.defer()
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📝 Подать заявку", style=discord.ButtonStyle.primary, custom_id="tier_application")
    async def application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TierApplication())
        except Exception as e:
            print(f"Ошибка при открытии модального окна: {e}")
            try:
                await interaction.response.send_message('❌ Ошибка открытия формы.', ephemeral=True)
            except:
                pass

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} успешно запущен на Railway!')
    print(f'📨 Категория для заявок: {CATEGORY_ID}')
    print(f'📋 Канал для логов: {LOG_CHANNEL_ID}')
    print(f'🎯 Разрешенные роли для команд: {ALLOWED_ROLE_IDS}')
    
    try:
        bot.add_view(ApplicationView())
        bot.add_view(ModerationView(0, 0, "", "", "", "", ""))
        print('✅ Views зарегистрированы')
        
        # Синхронизация команд
        try:
            synced = await bot.tree.sync()
            print(f'✅ Синхронизировано {len(synced)} команд')
        except Exception as e:
            print(f'❌ Ошибка синхронизации команд: {e}')
            
    except Exception as e:
        print(f'❌ Ошибка views: {e}')

@bot.tree.command(name="заявка", description="Создать панель заявок на Tier")
@has_allowed_role()
async def create_application_panel(interaction: discord.Interaction):
    """Создает панель заявок на Tier"""
    try:
        view = ApplicationView()
        embed = discord.Embed(
            title="🎯 Заявка на Tier",
            description="> Используй кнопку ниже чтобы отправить заявку на Tier",
            color=0x3498db
        )
        embed.add_field(name="📋 Формат", value="```Имя Фамилия | Статический ID\nПример: Skeet Amnyam | 2253```", inline=False)
        embed.add_field(name="📝 Требования", value="""
> ✵ **10 скринов** с 50+ киллов (imgur/ibb)
> ✵ **2 видео с арены** - полные 10-минутные (тяжка/спешик + сайга)
> ✵ **Видео с каптов** - со звуком, можно с других семей(по желанию, повышает шанс на более высокий тир (YouTube/Rutube))
> ✵ **Откаты с залазами** - [ССЫЛКА НА ЗАЛАЗЫ](https://docs.google.com/spreadsheets/d/1RWonpmIXoq5I80yqOcQ5X2OqyEzDuL-vXDXn9zQNAAM/edit?gid=2141313289#gid=2141313289)
> -> 1 6 7 10 15 - **Церовкь**
> -> 1 2 11 - **Завод** 
> -> 3 - **Пирс** 
> -> 12 - **Миррор** 
> -> 7 - **Сэндик** 
> -> 1 - **Яки** 
> -> 9 5 - **Палето** 
> -> 2 - **Дом Майкла**
> ✵ **MCL откаты** - по желанию, повышает шанс на более высокий тир (YouTube/Rutube)""", inline=False)
        embed.set_image(url="https://media.discordapp.net/attachments/1354522711895834646/1444635751198490704/maxresdefault.jpg?ex=692d6d63&is=692c1be3&hm=08f0a3666648dd1694c65b536d0e82490e42ef31497d8ebbc9decb0fe5fa6cd3&=&format=webp")
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Логируем создание панели
        await send_log(
            "📋 Панель заявок создана",
            interaction.user,
            f"Панель создана в канале: {interaction.channel.mention}",
            fields=[("👤 Создал", f"{interaction.user.mention} ({interaction.user.id})")]
        )
        
    except Exception as e:
        print(f"Ошибка команды заявка: {e}")
        await interaction.response.send_message("❌ Ошибка создания панели заявок", ephemeral=True)

@bot.tree.command(name="статус", description="Показать статус бота")
@has_allowed_role()
async def bot_status(interaction: discord.Interaction):
    """Показывает статус бота (только для разрешенных ролей)"""
    try:
        embed = discord.Embed(
            title="📊 Статус бота",
            color=0x3498db
        )
        
        embed.add_field(name="🤖 Бот", value=f"```{bot.user.name}```", inline=True)
        embed.add_field(name="🆔 ID бота", value=f"```{bot.user.id}```", inline=True)
        embed.add_field(name="📅 Запущен", value=f"```{discord.utils.format_dt(bot.user.created_at, 'R')}```", inline=False)
        
        embed.add_field(name="📨 Категория заявок", value=f"```ID: {CATEGORY_ID}```", inline=True)
        embed.add_field(name="📋 Канал логов", value=f"```ID: {LOG_CHANNEL_ID}```", inline=True)
        
        # Информация о гильдии
        guild = interaction.guild
        if guild:
            embed.add_field(name="🏰 Сервер", value=f"```{guild.name}```", inline=True)
            embed.add_field(name="👥 Участников", value=f"```{guild.member_count}```", inline=True)
        
        embed.add_field(name="⚡ Ping", value=f"```{round(bot.latency * 1000)}ms```", inline=True)
        
        embed.set_footer(text=f"Запросил: {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"Ошибка команды статус: {e}")
        await interaction.response.send_message("❌ Ошибка получения статуса", ephemeral=True)

@bot.tree.command(name="очистить", description="Очистить указанное количество сообщений")
@app_commands.describe(количество="Количество сообщений для очистки (1-100)")
@has_allowed_role()
async def clear_messages(interaction: discord.Interaction, количество: int):
    """Очищает указанное количество сообщений (только для разрешенных ролей)"""
    try:
        if количество < 1 or количество > 100:
            await interaction.response.send_message("❌ Количество должно быть от 1 до 100", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        deleted = await interaction.channel.purge(limit=количество)
        
        # Логируем очистку
        await send_log(
            "🧹 Сообщения очищены",
            interaction.user,
            f"Очищено {len(deleted)} сообщений в #{interaction.channel.name}",
            fields=[
                ("👤 Очистил", f"{interaction.user.mention} ({interaction.user.id})"),
                ("📊 Количество", str(len(deleted))),
                ("#️⃣ Канал", f"#{interaction.channel.name} (`{interaction.channel.id}`)")
            ]
        )
        
        await interaction.followup.send(f"✅ Очищено {len(deleted)} сообщений", ephemeral=True)
        
    except Exception as e:
        print(f"Ошибка команды очистить: {e}")
        await interaction.followup.send("❌ Ошибка при очистке сообщений", ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Обработчик ошибок для slash-команд"""
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ У вас нет прав для использования этой команды.\n"
            f"Требуемые роли: {', '.join([f'<@&{role_id}>' for role_id in ALLOWED_ROLE_IDS])}",
            ephemeral=True
        )
    else:
        print(f"Ошибка slash-команды: {error}")
        try:
            await interaction.response.send_message("❌ Произошла ошибка при выполнении команды", ephemeral=True)
        except:
            pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Ошибка команды: {error}")

if __name__ == "__main__":
    print("🔄 Запуск бота...")
    bot.run(TOKEN)