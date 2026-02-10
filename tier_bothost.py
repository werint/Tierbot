import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import os
import sys
from datetime import datetime
import time

print("🚀 Запуск бота на Railway...")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORY_ID = 1381679976486539334
LOG_CHANNEL_ID = 1448991378750046209
WARN_CHANNEL_ID = 1470220017403433056  # Канал для заявок на снятие варнов
ALLOWED_ROLE_IDS = [1310673963000528949, 1381682246678741022, 1223589384452833290]  # Роли с доступом к командам
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("❌ ОШИБКА: DISCORD_TOKEN не найден!")
    sys.exit(1)

print("✅ Токен найден, запускаем бота...")

# Глобальные переменные для rate limiting
last_request_time = 0
MIN_REQUEST_INTERVAL = 1.0  # Минимальное время между запросами (секунды)

async def safe_request(coroutine, retries=3, delay=2):
    """Безопасное выполнение запроса с повторными попытками"""
    for attempt in range(retries):
        try:
            return await coroutine
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limit
                wait_time = delay * (attempt + 1)
                print(f"⚠️ Rate limit, ждем {wait_time} секунд (попытка {attempt + 1}/{retries})")
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(delay)
    return None

async def send_log(action: str, user: discord.User, details: str = "", fields: list = None):
    """Отправляет лог в канал логов с обработкой rate limits"""
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
            
            # Добавляем небольшую задержку между запросами
            global last_request_time
            current_time = time.time()
            if current_time - last_request_time < MIN_REQUEST_INTERVAL:
                await asyncio.sleep(MIN_REQUEST_INTERVAL - (current_time - last_request_time))
            
            await safe_request(log_channel.send(embed=embed))
            last_request_time = time.time()
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

# ===================== КЛАССЫ ДЛЯ WARN ЗАЯВОК =====================

class WarnApplicationModal(ui.Modal, title='Заявка на снятие варна'):
    """Модальное окно для подачи заявки на снятие варна"""
    
    nickname = ui.TextInput(
        label='Ваш никнейм',
        placeholder='Пример: Skeet Amnyam',
        max_length=50
    )
    
    gg_links = ui.TextInput(
        label='Ссылки на 5 ггшек с 50+ киллов',
        placeholder='Ссылки на imgur/ibb (каждая с новой строки или через запятую)',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    mp_links = ui.TextInput(
        label='Ссылки на 5 присутствий на МП',
        placeholder='Ссылки на скриншоты/подтверждения (каждая с новой строки или через запятую)',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Проверяем, что хотя бы что-то заполнено
            if not self.gg_links.value and not self.mp_links.value:
                await interaction.followup.send(
                    "❌ Вы должны предоставить либо 5 ггшек, либо 5 подтверждений присутствия на МП!",
                    ephemeral=True
                )
                return
            
            # Получаем канал для заявок на варны
            warn_channel = bot.get_channel(WARN_CHANNEL_ID)
            if not warn_channel:
                await interaction.followup.send('❌ Ошибка: не найден канал для заявок на варны', ephemeral=True)
                return
            
            # Создаем embed с заявкой
            embed = discord.Embed(
                title=f"⚠️ Заявка на снятие варна от {self.nickname.value}",
                color=0xff9900,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="👤 Игрок", value=f"```{self.nickname.value}```", inline=False)
            embed.add_field(name="📞 Контакт", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            
            if self.gg_links.value:
                gg_value = self.gg_links.value[:500] + "..." if len(self.gg_links.value) > 500 else self.gg_links.value
                embed.add_field(name="🎯 5 ггшек с 50+ киллов", value=gg_value, inline=False)
            
            if self.mp_links.value:
                mp_value = self.mp_links.value[:500] + "..." if len(self.mp_links.value) > 500 else self.mp_links.value
                embed.add_field(name="📅 5 присутствий на МП", value=mp_value, inline=False)
            
            embed.set_footer(text=f"ID пользователя: {interaction.user.id} • {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            
            # Создаем view с кнопками для модерации
            view = WarnModerationView(
                applicant_id=interaction.user.id,
                applicant_name=self.nickname.value,
                gg_links=self.gg_links.value,
                mp_links=self.mp_links.value
            )
            
            # Отправляем заявку в канал
            message = await safe_request(warn_channel.send(embed=embed, view=view))
            
            if not message:
                await interaction.followup.send('❌ Ошибка: не удалось отправить заявку. Попробуйте позже.', ephemeral=True)
                return
            
            await interaction.followup.send(
                f'✅ Ваша заявка на снятие варна отправлена в {warn_channel.mention}!\n'
                f'Модераторы рассмотрят её в ближайшее время.',
                ephemeral=True
            )
            
            # Логируем создание заявки
            log_fields = [
                ("👤 Игрок", f"`{self.nickname.value}`"),
                ("📞 Контакт", f"{interaction.user.mention} ({interaction.user.id})"),
                ("🎯 Ггшки", self.gg_links.value[:800] if self.gg_links.value else "Не предоставлено"),
                ("📅 МП", self.mp_links.value[:800] if self.mp_links.value else "Не предоставлено"),
                ("#️⃣ Сообщение", f"[Перейти к заявке]({message.jump_url})")
            ]
            
            await send_log(
                "⚠️ Новая заявка на снятие варна",
                interaction.user,
                f"Заявка отправлена в {warn_channel.mention}",
                fields=log_fields
            )
            
        except Exception as e:
            print(f"Ошибка при создании заявки на варн: {e}")
            try:
                await interaction.followup.send('❌ Ошибка при отправке заявки.', ephemeral=True)
            except:
                pass

class WarnModerationView(discord.ui.View):
    """View с кнопками для модерации заявок на снятие варна"""
    
    def __init__(self, applicant_id, applicant_name, gg_links, mp_links):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.applicant_name = applicant_name
        self.gg_links = gg_links
        self.mp_links = mp_links
        self.decision_made = False
    
    @discord.ui.button(label="✅ Принять заявку", style=discord.ButtonStyle.success, custom_id="warn_accept")
    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Принять заявку на снятие варна"""
        try:
            # Проверяем права через декоратор
            user_roles = [role.id for role in interaction.user.roles]
            has_allowed = any(role_id in user_roles for role_id in ALLOWED_ROLE_IDS)
            has_perms = interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_messages
            
            if not has_allowed and not has_perms:
                await interaction.response.send_message("❌ У вас нет прав для принятия заявок.", ephemeral=True)
                return
            
            if self.decision_made:
                await interaction.response.send_message("❌ По этой заявке уже было принято решение.", ephemeral=True)
                return
            
            self.decision_made = True
            
            # Сначала отправляем ответ
            await interaction.response.defer(ephemeral=True)
            
            # Отключаем кнопки
            for child in self.children:
                child.disabled = True
            
            # Обновляем embed
            embed = interaction.message.embeds[0]
            embed.color = 0x00ff00  # Зеленый цвет
            embed.title = f"✅ ЗАЯВКА ПРИНЯТА - {self.applicant_name}"
            embed.add_field(
                name="✅ Решение",
                value=f"Заявка принята {interaction.user.mention}\nВарн снят!",
                inline=False
            )
            
            # Редактируем сообщение с задержкой
            await asyncio.sleep(0.5)
            await safe_request(interaction.message.edit(embed=embed, view=self))
            
            await interaction.followup.send(f"✅ Заявка от {self.applicant_name} принята!", ephemeral=True)
            
            # Уведомляем заявителя
            try:
                applicant = await interaction.guild.fetch_member(self.applicant_id)
                if applicant:
                    dm_embed = discord.Embed(
                        title="✅ Ваша заявка на снятие варна принята!",
                        description=f"Ваша заявка на снятие варна была рассмотрена и **ПРИНЯТА** модератором {interaction.user.mention}.",
                        color=0x00ff00,
                        timestamp=discord.utils.utcnow()
                    )
                    dm_embed.add_field(name="👤 Модератор", value=interaction.user.mention, inline=False)
                    dm_embed.add_field(name="🎯 Ваш никнейм", value=f"`{self.applicant_name}`", inline=False)
                    dm_embed.set_footer(text=f"Решение принято: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
                    
                    await asyncio.sleep(0.5)
                    await safe_request(applicant.send(embed=dm_embed))
            except Exception as e:
                print(f"Не удалось отправить DM пользователю: {e}")
            
            # Логируем принятие заявки
            log_fields = [
                ("✅ Решение", "ПРИНЯТО"),
                ("👤 Игрок", f"`{self.applicant_name}`"),
                ("📞 Заявитель", f"<@{self.applicant_id}>"),
                ("👨‍⚖️ Модератор", f"{interaction.user.mention} ({interaction.user.id})"),
                ("🎯 Ггшки", "Предоставлены" if self.gg_links else "Не предоставлены"),
                ("📅 МП", "Предоставлены" if self.mp_links else "Не предоставлены"),
                ("#️⃣ Сообщение", f"[Перейти к заявке]({interaction.message.jump_url})")
            ]
            
            await send_log(
                "✅ Заявка на варн принята",
                interaction.user,
                f"Заявка от {self.applicant_name} принята",
                fields=log_fields
            )
            
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit при принятии заявки: {e}")
                try:
                    await interaction.followup.send(
                        "⚠️ Discord API перегружен. Пожалуйста, попробуйте позже.",
                        ephemeral=True
                    )
                except:
                    pass
            else:
                print(f"Ошибка при принятии заявки: {e}")
                try:
                    await interaction.followup.send("❌ Ошибка при обработке заявки.", ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Другая ошибка при принятии заявки: {e}")
            try:
                await interaction.followup.send("❌ Ошибка при обработке заявки.", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="❌ Отклонить заявку", style=discord.ButtonStyle.danger, custom_id="warn_reject")
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отклонить заявку на снятие варна"""
        try:
            # Проверяем права через декоратор
            user_roles = [role.id for role in interaction.user.roles]
            has_allowed = any(role_id in user_roles for role_id in ALLOWED_ROLE_IDS)
            has_perms = interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_messages
            
            if not has_allowed and not has_perms:
                await interaction.response.send_message("❌ У вас нет прав для отклонения заявок.", ephemeral=True)
                return
            
            if self.decision_made:
                await interaction.response.send_message("❌ По этой заявке уже было принято решение.", ephemeral=True)
                return
            
            # Создаем модальное окно и передаем ему ссылку на этот view
            modal = WarnRejectModal(parent_view=self)
            await interaction.response.send_modal(modal)
            
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit при открытии модального окна: {e}")
                try:
                    await interaction.response.send_message(
                        "⚠️ Слишком много запросов. Пожалуйста, подождите несколько секунд.",
                        ephemeral=True
                    )
                except:
                    pass
            else:
                print(f"Ошибка при открытии модального окна: {e}")
                try:
                    await interaction.response.send_message("❌ Ошибка при открытии формы.", ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Другая ошибка при открытии модального окна: {e}")
            try:
                await interaction.response.send_message("❌ Ошибка при открытии формы.", ephemeral=True)
            except:
                pass

class WarnRejectModal(ui.Modal, title='Укажите причину отказа'):
    """Модальное окно для указания причины отказа"""
    
    def __init__(self, parent_view):
        super().__init__(timeout=300)  # 5 минут timeout
        self.parent_view = parent_view
        
        self.reason = ui.TextInput(
            label='Причина отклонения заявки',
            placeholder='Опишите причину отклонения заявки...',
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if not self.parent_view:
                await interaction.followup.send("❌ Ошибка: не найдена информация о заявке.", ephemeral=True)
                return
            
            # Проверяем, не принято ли уже решение
            if self.parent_view.decision_made:
                await interaction.followup.send("❌ По этой заявке уже было принято решение.", ephemeral=True)
                return
            
            # Отмечаем, что решение принято
            self.parent_view.decision_made = True
            
            # Отключаем все кнопки в view
            for child in self.parent_view.children:
                child.disabled = True
            
            # Получаем сообщение
            message = interaction.message
            
            # Обновляем embed
            embed = message.embeds[0].copy()
            embed.color = 0xff0000  # Красный цвет
            embed.title = f"❌ ЗАЯВКА ОТКЛОНЕНА - {self.parent_view.applicant_name}"
            
            # Добавляем поле с решением
            embed.add_field(
                name="❌ Решение",
                value=f"Заявка отклонена {interaction.user.mention}\n**Причина:** {self.reason.value}",
                inline=False
            )
            
            # Редактируем сообщение
            await asyncio.sleep(0.5)
            await safe_request(message.edit(embed=embed, view=self.parent_view))
            
            # Уведомляем заявителя
            try:
                applicant = await interaction.guild.fetch_member(self.parent_view.applicant_id)
                if applicant:
                    dm_embed = discord.Embed(
                        title="❌ Ваша заявка на снятие варна отклонена",
                        description=f"Ваша заявка на снятие варна была рассмотрена и **ОТКЛОНЕНА** модератором {interaction.user.mention}.",
                        color=0xff0000,
                        timestamp=discord.utils.utcnow()
                    )
                    dm_embed.add_field(name="👤 Модератор", value=interaction.user.mention, inline=False)
                    dm_embed.add_field(name="🎯 Ваш никнейм", value=f"`{self.parent_view.applicant_name}`", inline=False)
                    dm_embed.add_field(name="📝 Причина отказа", value=self.reason.value, inline=False)
                    dm_embed.set_footer(text=f"Решение принято: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
                    
                    await asyncio.sleep(0.5)
                    await safe_request(applicant.send(embed=dm_embed))
            except Exception as e:
                print(f"Не удалось отправить DM пользователю: {e}")
            
            # Логируем отклонение заявки
            log_fields = [
                ("❌ Решение", "ОТКЛОНЕНО"),
                ("👤 Игрок", f"`{self.parent_view.applicant_name}`"),
                ("📞 Заявитель", f"<@{self.parent_view.applicant_id}>"),
                ("👨‍⚖️ Модератор", f"{interaction.user.mention} ({interaction.user.id})"),
                ("📝 Причина", self.reason.value),
                ("🎯 Ггшки", "Предоставлены" if self.parent_view.gg_links else "Не предоставлены"),
                ("📅 МП", "Предоставлены" if self.parent_view.mp_links else "Не предоставлены"),
                ("#️⃣ Сообщение", f"[Перейти к заявке]({message.jump_url})")
            ]
            
            await send_log(
                "❌ Заявка на варн отклонена",
                interaction.user,
                f"Заявка от {self.parent_view.applicant_name} отклонена",
                fields=log_fields
            )
            
            await interaction.followup.send(f"✅ Заявка от {self.parent_view.applicant_name} отклонена!", ephemeral=True)
            
        except Exception as e:
            print(f"Ошибка при обработке отклонения заявки: {e}")
            try:
                await interaction.followup.send("❌ Ошибка при обработке заявки.", ephemeral=True)
            except:
                pass

class WarnApplicationView(discord.ui.View):
    """View с кнопкой для подачи заявки на снятие варна"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📝 Подать заявку", style=discord.ButtonStyle.primary, custom_id="warn_apply_button")
    async def application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(WarnApplicationModal())
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit при открытии модального окна для варна: {e}")
                try:
                    await interaction.response.send_message(
                        "⚠️ Слишком много запросов. Пожалуйста, подождите несколько секунд.",
                        ephemeral=True
                    )
                except:
                    pass
            else:
                print(f"Ошибка при открытии модального окна для варна: {e}")
                try:
                    await interaction.response.send_message('❌ Ошибка открытия формы.', ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Другая ошибка при открытии модального окна для варна: {e}")
            try:
                await interaction.response.send_message('❌ Ошибка открытия формы.', ephemeral=True)
            except:
                pass

# ===================== СУЩЕСТВУЮЩИЙ КОД (Tier Application) =====================

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

            channel = await safe_request(category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Заявка на Tier от {interaction.user.display_name}"
            ))
            
            if not channel:
                await interaction.followup.send('❌ Ошибка: не удалось создать канал', ephemeral=True)
                return
            
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
            
            await asyncio.sleep(0.5)
            await safe_request(channel.send(embed=embed, view=view))
            await asyncio.sleep(0.5)
            await safe_request(channel.send(f"👤 Заявитель: {interaction.user.mention}"))
            
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
        try:
            if self.taken:
                await interaction.response.defer()
                return
            
            self.taken = True
            button.disabled = True
            button.label = "✅ На рассмотрении"
            
            await safe_request(interaction.message.edit(view=self))
            await asyncio.sleep(0.5)
            await safe_request(interaction.channel.send(f"📋 **Заявка взята на рассмотрение** {interaction.user.mention}"))
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
            
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit при взятии на рассмотрение: {e}")
            else:
                print(f"Ошибка при взятии на рассмотрение: {e}")
            await interaction.response.defer()
    
    @discord.ui.button(label="❌ Закрыть заявку", style=discord.ButtonStyle.danger, custom_id="close_application")
    async def close_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
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
            
            await interaction.response.defer()
            await asyncio.sleep(0.5)
            await safe_request(interaction.channel.send(f"🔒 **Заявка закрыта** {interaction.user.mention}\nКанал удалится через 5 секунд..."))
            
            await asyncio.sleep(5)
            await safe_request(interaction.channel.delete())
            
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit при закрытии заявки: {e}")
                try:
                    await interaction.response.send_message("⚠️ Discord API перегружен. Попробуйте позже.", ephemeral=True)
                except:
                    pass
            else:
                print(f"Ошибка при закрытии заявки: {e}")
                try:
                    await interaction.response.send_message("❌ Ошибка при закрытии заявки.", ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Другая ошибка при закрытии заявки: {e}")
            try:
                await interaction.response.send_message("❌ Ошибка при закрытии заявки.", ephemeral=True)
            except:
                pass

class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📝 Подать заявку", style=discord.ButtonStyle.primary, custom_id="tier_application")
    async def application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TierApplication())
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit при открытии модального окна: {e}")
                try:
                    await interaction.response.send_message(
                        "⚠️ Слишком много запросов. Пожалуйста, подождите несколько секунд.",
                        ephemeral=True
                    )
                except:
                    pass
            else:
                print(f"Ошибка при открытии модального окна: {e}")
                try:
                    await interaction.response.send_message('❌ Ошибка открытия формы.', ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Другая ошибка при открытии модального окна: {e}")
            try:
                await interaction.response.send_message('❌ Ошибка открытия формы.', ephemeral=True)
            except:
                pass

# ===================== КОМАНДЫ =====================

@bot.tree.command(name="warn", description="Создать панель заявок на снятие варна")
@has_allowed_role()
async def create_warn_panel(interaction: discord.Interaction):
    """Создает панель заявок на снятие варна"""
    try:
        view = WarnApplicationView()
        embed = discord.Embed(
            title="⚠️ Снятие варна/обжалование варна",
            description="> Используй кнопку ниже чтобы подать заявку на снятие варна",
            color=0xff9900
        )
        
        embed.add_field(
            name="📋 Условия для снятия варна:",
            value="""
> Вы должны выполнить **ОДНО** из условий:
> 
> **🎯 Вариант 1:** 5 ггшек с 50+ киллов
> **📅 Вариант 2:** Присутствие на 5 МП
> 
> ⚠️ **ВАЖНО:** 
> - Учитываются только те ггшки и МП, которые были сделаны **ПОСЛЕ** выданного варна
> - Если вам нужно обжаловать варн, то доказательства прикрепите в любую из строк
""",
            inline=False
        )
        
        embed.set_footer(text="В лс придет результат, с любовью Skeet<3")
        embed.set_image(url="https://i.ytimg.com/vi/g-SiUWFmQ94/maxresdefault.jpg?sqp=-oaymwEmCIAKENAF8quKqQMa8AEB-AHUBoAC4AOKAgwIABABGGQgZChkMA8=&rs=AOn4CLBXZYgL89IRNlWkLYeBYPf6RHdSIw")
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Логируем создание панели
        await send_log(
            "⚠️ Панель заявок на варн создана",
            interaction.user,
            f"Панель создана в канале: {interaction.channel.mention}",
            fields=[("👤 Создал", f"{interaction.user.mention} ({interaction.user.id})")]
        )
        
    except Exception as e:
        print(f"Ошибка команды warn: {e}")
        await interaction.response.send_message("❌ Ошибка создания панели заявок на варн", ephemeral=True)

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
> ✵ **Откаты с залазами** - [ССЫЛКА НА ЗАЛАЗЫ](https://docs.google.com/spreadsheets/d/1RWonpmIXoq5I80yqOcQ5X2OqyEzDuL-vXDXn9zQNAAM/edit?gid=2141313289#gid=2141313289)
> -> 1 6 7 10 15 - **Церовкь**
> -> 1 2 11 - **Завод** 
> -> 3 - **Пирс** 
> -> 12 - **Миррор** 
> -> 7 - **Сэндик** 
> -> 1 - **Яки** 
> -> 9 5 - **Палето** 
> -> 2 - **Дом Майкла**
> ✵ **Капты и MCL откаты** - по желанию, повышает шанс на более высокий тир (YouTube/Rutube)""", inline=False)
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
        embed.add_field(name="⚠️ Канал варнов", value=f"```ID: {WARN_CHANNEL_ID}```", inline=True)
        
        # Информация о гильдии
        guild = interaction.guild
        if guild:
            embed.add_field(name="🏰 Сервер", value=f"```{guild.name}```", inline=True)
            embed.add_field(name="👥 Участников", value=f"```{guild.member_count}```", inline=True)
        
        embed.add_field(name="⚡ Ping", value=f"```{round(bot.latency * 1000)}ms```", inline=True)
        
        # Подсчитываем количество заявок
        tier_count = 0
        try:
            category = bot.get_channel(CATEGORY_ID)
            if category and isinstance(category, discord.CategoryChannel):
                tier_count = len([ch for ch in category.channels if isinstance(ch, discord.TextChannel)])
        except:
            pass
        
        warn_count = 0
        try:
            warn_channel = bot.get_channel(WARN_CHANNEL_ID)
            if warn_channel:
                async for message in warn_channel.history(limit=100):
                    if message.embeds and "Заявка на снятие варна" in message.embeds[0].title:
                        warn_count += 1
        except:
            pass
        
        embed.add_field(name="📊 Активные заявки", value=f"```Tier: {tier_count} | Warn: {warn_count}```", inline=False)
        
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
        
        deleted = await safe_request(interaction.channel.purge(limit=количество))
        
        if not deleted:
            deleted = []
        
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

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} успешно запущен на Railway!')
    print(f'📨 Категория для заявок: {CATEGORY_ID}')
    print(f'📋 Канал для логов: {LOG_CHANNEL_ID}')
    print(f'⚠️ Канал для заявок на варны: {WARN_CHANNEL_ID}')
    print(f'🎯 Разрешенные роли для команд: {ALLOWED_ROLE_IDS}')
    
    try:
        # Регистрируем все views
        bot.add_view(ApplicationView())
        bot.add_view(ModerationView(0, 0, "", "", "", "", ""))
        bot.add_view(WarnApplicationView())
        # WarnModerationView не регистрируем здесь - он создается динамически для каждой заявки
        print('✅ Views зарегистрированы')
        
        # Синхронизация команд
        try:
            synced = await bot.tree.sync()
            print(f'✅ Синхронизировано {len(synced)} команд')
        except Exception as e:
            print(f'❌ Ошибка синхронизации команд: {e}')
            
    except Exception as e:
        print(f'❌ Ошибка views: {e}')

if __name__ == "__main__":
    print("🔄 Запуск бота...")
    bot.run(TOKEN)