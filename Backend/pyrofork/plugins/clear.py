from pyrogram import filters, Client, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Backend.helper.custom_filter import CustomFilters
from Backend import db
from Backend.helper.task_manager import delete_message
from Backend.helper.encrypt import decode_string
import asyncio

@Client.on_message(filters.command('clear') & filters.private & CustomFilters.owner)
async def clear_command(client: Client, message: Message):
    await message.reply_text(
        "**⚠️ Are you sure you want to delete all data?**\n\n"
        "This action is irreversible and will delete all movies, TV shows, and database entries.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Yes, I'm sure", callback_data="confirm_clear"),
                    InlineKeyboardButton("❌ No, cancel", callback_data="cancel_clear")
                ]
            ]
        ),
        quote=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )

from Backend.config import Telegram

@Client.on_callback_query(filters.regex(r"^confirm_clear$") & CustomFilters.owner)
async def confirm_clear_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text("⏳ **Checking permissions...**")

    auth_channels = Telegram.AUTH_CHANNEL
    for channel_id in auth_channels:
        try:
            channel = await client.get_chat(int(channel_id))
            member = await channel.get_member(client.me.id)
            if not member.privileges.can_delete_messages:
                await callback_query.edit_message_text(f"❌ **Error:** I don't have permission to delete messages in {channel.title} (`{channel_id}`). Please grant me the required permissions and try again.")
                return
        except Exception as e:
            await callback_query.edit_message_text(f"❌ **Error:** Could not verify permissions in channel `{channel_id}`. Please make sure I am a member and an administrator.\n\n`{e}`")
            return

    await callback_query.edit_message_text("✅ **Permissions verified.**\n\n⏳ **Fetching all media file IDs...**")
    file_ids = await db.get_all_media_files()

    if not file_ids:
        await callback_query.edit_message_text("✅ **No data to delete.**")
        return

    await callback_query.edit_message_text(f"⏳ **Deleting {len(file_ids)} Telegram files...**\n\nThis may take a while. Please be patient.")

    deletion_tasks = []
    for file_id in file_ids:
        try:
            decoded_data = await decode_string(file_id)
            chat_id = int(f"-100{decoded_data['chat_id']}")
            msg_id = int(decoded_data['msg_id'])
            deletion_tasks.append(delete_message(chat_id, msg_id))
        except Exception as e:
            print(f"Failed to decode or queue file for deletion: {e}")

    successful_deletions = 0
    failed_deletions = 0

    if deletion_tasks:
        results = await asyncio.gather(*deletion_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                failed_deletions += 1
            else:
                successful_deletions += 1

    await callback_query.edit_message_text(f"✅ **File deletion complete.**\n\n- Successfully deleted: {successful_deletions}\n- Failed to delete: {failed_deletions}\n\n⏳ **Dropping database collections...**")

    deleted_count = await db.drop_all_media_collections()
    await callback_query.edit_message_text(f"✅ **Operation complete.**\n\n- Successfully deleted files: {successful_deletions}\n- Failed to delete files: {failed_deletions}\n- Deleted database documents: {deleted_count}")

@Client.on_callback_query(filters.regex(r"^cancel_clear$") & CustomFilters.owner)
async def cancel_clear_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text("❌ **Operation cancelled.**")
