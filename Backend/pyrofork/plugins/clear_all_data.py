from pyrogram import filters, Client, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Backend.helper.custom_filter import CustomFilters
from Backend import db
from Backend.helper.task_manager import delete_message
from Backend.helper.encrypt import decode_string
import asyncio

@Client.on_message(filters.command('clear_all_data') & filters.private & CustomFilters.owner)
async def clear_all_data_command(client: Client, message: Message):
    await message.reply_text(
        "**⚠️ Are you sure you want to delete all data?**\n\n"
        "This action is irreversible and will delete all movies, TV shows, and database entries.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Yes, I'm sure", callback_data="confirm_clear_data"),
                    InlineKeyboardButton("❌ No, cancel", callback_data="cancel_clear_data")
                ]
            ]
        ),
        quote=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r"^confirm_clear_data$") & CustomFilters.owner)
async def confirm_clear_data_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text("⏳ **Fetching all media file IDs...**")
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

    if deletion_tasks:
        await asyncio.gather(*deletion_tasks, return_exceptions=True)

    await callback_query.edit_message_text("⏳ **Dropping database collections...**")
    deleted_count = await db.drop_all_media_collections()
    await callback_query.edit_message_text(f"✅ **Successfully deleted {deleted_count} documents and all associated files.**")

@Client.on_callback_query(filters.regex(r"^cancel_clear_data$") & CustomFilters.owner)
async def cancel_clear_data_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text("❌ **Operation cancelled.**")
