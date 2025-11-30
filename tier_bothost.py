import discord
from discord.ext import commands
from discord import ui
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ID категории где создавать каналы
CATEGORY_ID = 1381679976486539334

# Получаем токен из переменных окружения
TOKEN = os.getenv('DISCORD_TOKEN')

class TierApplication(ui.Modal, title='Заявка на Tier'):
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
        label='3 видео с каптов (последние 3)',
        placeholder='Ссылки на видео со звуком',
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    rp_mcl_videos = ui.TextInput(
        label='RP откаты (2) + MCL (по желанию)',
        placeholder='Сначала 2 RP отката, затем MCL если есть',
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Создаем канал для заявки
            category = bot.get_channel(CATEGORY_ID)
            if not category:
                await interaction.followup.send(
                    '❌ Ошибка: не найдена категория для заявок', 
                    ephemeral=True
                )
                return

            # Создаем канал с именем Tier-никнейм
            channel_name = f"tier-{interaction.user.display_name}"[:100]
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Добавляем права для администраторов/модераторов
            for role in interaction.guild.roles:
                if role.permissions.administrator or role.permissions.manage_messages:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            channel = await category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Заявка на Tier от {interaction.user.display_name}"
            )
            
            # Создаем embed с заявкой в новом канале
            embed = discord.Embed(
                title=f"🎯 Заявка на Tier от {interaction.user.display_name}",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="👤 Игрок", 
                value=f"```{self.nickname}```", 
                inline=False
            )
            
            embed.add_field(
                name="📸 10 скринов с 50+ киллов", 
                value=f"{self.screenshots.value[:500]}..." if len(self.screenshots.value) > 500 else self.screenshots.value, 
                inline=False
            )
            
            embed.add_field(
                name="🎮 2 видео с арены", 
                value=f"{self.arena_videos.value[:500]}..." if len(self.arena_videos.value) > 500 else self.arena_videos.value, 
                inline=False
            )
            
            embed.add_field(
                name="⚔️ 3 видео с каптов", 
                value=f"{self.capt_videos.value[:500]}..." if len(self.capt_videos.value) > 500 else self.capt_videos.value, 
                inline=False
            )
            
            embed.add_field(
                name="🎭 RP + MCL откаты", 
                value=f"{self.rp_mcl_videos.value[:500]}..." if len(self.rp_mcl_videos.value) > 500 else self.rp_mcl_videos.value, 
                inline=False
            )
            
            embed.set_footer(text=f"ID пользователя: {interaction.user.id}")
            
            # Создаем view с кнопками
            view = ModerationView(interaction.user.id)
            
            # Отправляем заявку в новый канал
            await channel.send(embed=embed, view=view)
            await channel.send(f"👤 Заявитель: {interaction.user.mention}")
            
            await interaction.followup.send(
                f'✅ Ваша заявка успешно создана! Перейдите в канал {channel.mention}', 
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Ошибка при создании заявки: {e}")
            try:
                await interaction.followup.send(
                    '❌ Произошла ошибка при создании заявки. Попробуйте еще раз.', 
                    ephemeral=True
                )
            except:
                pass

class ModerationView(discord.ui.View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.taken = False
    
    @discord.ui.button(label="✅ Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_review")
    async def take_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.taken:
            try:
                await interaction.response.send_message("❌ Эта заявка уже взята на рассмотрение!", ephemeral=True)
            except:
                await interaction.followup.send("❌ Эта заявка уже взята на рассмотрение!", ephemeral=True)
            return
        
        self.taken = True
        button.disabled = True
        button.label = "✅ На рассмотрении"
        
        # Обновляем сообщение
        await interaction.message.edit(view=self)
        
        # Отправляем сообщение о взятии на рассмотрение
        await interaction.channel.send(
            f"📋 **Заявка взята на рассмотрение** {interaction.user.mention}\n"
        )
    
    
    @discord.ui.button(label="❌ Закрыть заявку", style=discord.ButtonStyle.danger, custom_id="close_application")
    async def close_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверяем права
        if not interaction.user.guild_permissions.manage_messages and not interaction.user.guild_permissions.administrator:
            try:
                await interaction.response.send_message("❌ У вас нет прав для закрытия заявок!", ephemeral=True)
            except:
                await interaction.followup.send("❌ У вас нет прав для закрытия заявок!", ephemeral=True)
            return
        
        # Отправляем сообщение о закрытии
        await interaction.channel.send(
            f"🔒 **Заявка закрыта** {interaction.user.mention}\n"
            f"Канал будет удален через 5 секунд..."
        )
        
        try:
            await interaction.response.send_message("✅ Заявка закрыта!", ephemeral=True)
        except:
            await interaction.followup.send("✅ Заявка закрыта!", ephemeral=True)
        
        # Ждем 5 секунд и удаляем канал
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
                await interaction.response.send_message(
                    '❌ Не удалось открыть форму заявки. Попробуйте позже.', 
                    ephemeral=True
                )
            except:
                try:
                    await interaction.followup.send(
                        '❌ Не удалось открыть форму заявки. Попробуйте позже.', 
                        ephemeral=True
                    )
                except:
                    pass

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен на Railway!')
    print(f'📨 Заявки будут создаваться в категории: {CATEGORY_ID}')
    try:
        bot.add_view(ApplicationView())
        bot.add_view(ModerationView(0))
        print('✅ Views зарегистрированы')
    except Exception as e:
        print(f'❌ Ошибка при регистрации views: {e}')

@bot.command()
async def заявка(ctx):
    """Отправляет кнопку для подачи заявки"""
    try:
        view = ApplicationView()
        
        embed = discord.Embed(
            title="🎯 Заявка на Tier",
            description="> Используй кнопку ниже чтобы отправить заявку на Tier",
            color=0x3498db
        )
        
        embed.add_field(
            name="📋 Формат", 
            value="```Имя Фамилия | Статический ID\nПример: Skeet Amnyam | 2253```",
            inline=False
        )
        
        embed.add_field(
            name="📝 Требования", 
            value="""
> ✵ **10 скринов** с 50+ киллов (imgur/ibb)
> ✵ **2 видео с арены** - полные 10-минутные (тяжка/спешик + сайга)
> ✵ **3 видео с каптов** - последние 3, со звуком
> ✵ **2 отката с RP** - поставка/дроп/цеха (YouTube/Rutube)
> ✵ **MCL откаты** - по желанию (YouTube/Rutube)
        """,
            inline=False
        )
        
        embed.set_image(url="https://media.discordapp.net/attachments/1354522711895834646/1444635751198490704/maxresdefault.jpg?ex=692d6d63&is=692c1be3&hm=08f0a3666648dd1694c65b536d0e82490e42ef31497d8ebbc9decb0fe5fa6cd3&=&format=webp")
        
        await ctx.send(embed=embed, view=view)
        
    except Exception as e:
        print(f"Ошибка при отправке команды заявка: {e}")
        await ctx.send("❌ Произошла ошибка при создании заявки")

# Обработка ошибки команды
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Ошибка команды: {error}")

# Запуск бота
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Ошибка: DISCORD_TOKEN не установлен")
        exit(1)
    bot.run(TOKEN)