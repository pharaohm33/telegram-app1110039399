import asyncio
import random
import time
from telethon import TelegramClient, events
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import InputPeerUser
from telethon.errors import SessionPasswordNeededError, UserNotMutualContactError, ChatAdminRequiredError, ChatWriteForbiddenError, FloodWaitError

api_id = '18115490'
api_hash = '4c21921adc9ba842c127173763b6e55e'
phone_number = '+13137620344' #no spaces or dashes remember add plus sign in beginning for +1 US numbers
admin_id = 1032127276 # user id telegram found using userinfobot

client = TelegramClient('S1', api_id, api_hash)

group_1 = None
group_2 = None
average_time_per_user = 90
is_stopped = False
is_running = False

@client.on(events.NewMessage)
async def handler(event):
    global group_1, group_2, is_stopped, is_running

    if event.sender_id != admin_id:
        return
    
    if event.raw_text == "ping":
        await event.respond("PONG!")
        return

    if "group1" in event.raw_text:
        link = event.raw_text.split("group1 ")[1]
        if link.startswith("https://t.me/") or link.startswith("t.me/"):
            group_1_id = await get_group_id_from_link(link)
            if group_1_id:
                group_1 = group_1_id
                await event.respond("Group 1 has been set using the link.")
                await event.respond(group_1)
            else:
                await event.respond("Failed to get Group 1 ID from the link.")
        elif link.startswith("-100"):
            try:
                group_1 = int(link)
                await join_group(group_1)
                await event.respond("Group 1 has been set and joined using the group ID.")
            except Exception as e:
                await event.respond(f"Failed to join Group 1 using the group ID: {e}")
        else:
            await event.respond("Invalid link or ID. Please provide a valid group or invite link.")

    elif "group2" in event.raw_text:
        link = event.raw_text.split("group2 ")[1]
        if link.startswith("https://t.me/") or link.startswith("t.me/"):
            group_2_id = await get_group_id_from_link(link)
            if group_2_id:
                group_2 = group_2_id
                await event.respond("Group 2 has been set using the link.")
                await join_group(group_2)
            else:
                await event.respond("Failed to get Group 2 ID from the link.")
        elif link.startswith("-100"):
            try:
                group_2 = int(link)
                await join_group(group_2)
                await event.respond("Group 2 has been set and joined using the group ID.")
            except Exception as e:
                await event.respond(f"Failed to join Group 2 using the group ID: {e}")
        else:
            await event.respond("Invalid link or ID. Please provide a valid group or invite link.")

    elif "start" in event.raw_text and group_1 and group_2:
        if is_running:
            await event.respond("Another operation is currently running. Please wait for it to finish.")
            return
        is_stopped = False
        is_running = True
        await event.respond("Starting to add users from Group 1 to Group 2...")

        if await group_has_hidden_participants(group_1):
            await event.respond("Group 1 has hidden participants. Adding senders of the last 1000 messages.")
            await add_users_from_messages(group_1, group_2, event)
        else:
            participants = await client.get_participants(group_1)
            total_participants = len(participants)
            estimated_total_time = (total_participants * average_time_per_user) // 60
            await event.respond(f"Group 1 has {total_participants} members. Estimated total time to add them: {estimated_total_time} minutes.")
            await add_users_to_group(group_1, group_2, event)

        is_running = False

    elif "stop" in event.raw_text:
        is_stopped = True
        await event.respond("The operation has been stopped.")

    else:
        await event.respond("Please set both groups first using 'group1 [link]' and 'group2 [link]'.")


async def join_group(group_id):
    try:
        await client(JoinChannelRequest(group_id))
        print(f"Successfully joined the group with ID {group_id}.")
    except FloodWaitError as e:
        print(f"Flood wait error: {e}.")
        await asyncio.sleep(e.x)
    except SessionPasswordNeededError:
        print("Two-step verification is enabled on your account. Please enter your password.")
        # Consider implementing a method to handle this
    except UserNotMutualContactError:
        print("You cannot join the group because you are not a mutual contact with its members.")
        # Ensure the group allows you to join
    except ChatAdminRequiredError:
        print("You need to be an admin to perform this action.")
        # Make sure you have admin rights
    except ChatWriteForbiddenError:
        print("You don't have permission to send messages in this chat.")
        # Ensure you have the right permissions
    except Exception as e:
        print(f"Failed to join the group with ID {group_id}: {e}")

async def get_group_id_from_link(link):
    try:
        entity = await client.get_entity(link)
        return entity.id
    except ValueError as e:
        print(f"ValueError: {e}. The link might be invalid or inaccessible.")
    except Exception as e:
        print(f"Error getting group ID from link: {e}")
    return None


async def group_has_hidden_participants(group_id):
    try:
        participants = await client.get_participants(group_id)
        return len(participants) == 0
    except Exception as e:
        print(f"Error checking hidden participants: {e}")
        return True

async def add_users_from_messages(group_1, group_2, event):
    global is_stopped

    senders = set()

    async for message in client.iter_messages(group_1, limit=1000):
        if message.sender_id:
            senders.add(message.sender_id)

    total_senders = len(senders)
    added_count = 0

    for i, sender_id in enumerate(senders, 1):
        if is_stopped:
            await event.respond(f"Operation stopped. {added_count} users were added.")
            break

        try:
            user = await client.get_entity(sender_id)
            await client(InviteToChannelRequest(group_2, [InputPeerUser(user.id, user.access_hash)]))
            added_count += 1

            remaining_users = total_senders - i
            estimated_time_left = remaining_users * average_time_per_user

            if i % 10 == 0:
                await event.respond(f"Progress: {i}/{total_senders} users processed. Estimated time left: {int(estimated_time_left // 60)} minutes.")

            delay = random.randint(60, 120)
            await asyncio.sleep(delay)

        except FloodWaitError as e:
            print(f"Flood wait error: {e}.")
            await asyncio.sleep(e.x)
        except Exception as e:
            print(f"Error adding user {sender_id}: {e}")
            delay = random.randint(30, 60)
            await asyncio.sleep(delay)

async def add_users_to_group(group_1, group_2, event):
    global is_stopped

    start_time = time.time()

    try:
        participants = await client.get_participants(group_1)
        total_participants = len(participants)
    except Exception as e:
        print(f"Error getting participants from group 1: {e}")
        return

    user_ids = {participant.id for participant in participants}

    try:
        group_2_participants = await client.get_participants(group_2)
        group_2_ids = {p.id for p in group_2_participants}
    except Exception as e:
        print(f"Error getting participants from group 2: {e}")
        return

    added_count = 0

    for i, user_id in enumerate(user_ids, 1):
        if is_stopped:
            await event.respond(f"Operation stopped. {added_count} users were added.")
            break

        if user_id in group_2_ids:
            continue

        try:
            user = await client.get_entity(user_id)
            await client(InviteToChannelRequest(group_2, [InputPeerUser(user.id, user.access_hash)]))
            added_count += 1

            remaining_users = total_participants - i
            estimated_time_left = remaining_users * average_time_per_user

            if i % 10 == 0:
                await event.respond(f"Progress: {i}/{total_participants} users processed. Estimated time left: {int(estimated_time_left // 60)} minutes.")

            delay = random.randint(600, 900)
            await asyncio.sleep(delay)

        except FloodWaitError as e:
            print(f"Flood wait error: {e}.")
            await asyncio.sleep(e.x)
        except Exception as e:
            print(f"Error adding user {user_id}: {e}")
            delay = random.randint(30, 60)
            await asyncio.sleep(delay)

    total_time = time.time() - start_time
    if not is_stopped:
        await event.respond(f"Added {added_count} users out of {total_participants}. Total time: {int(total_time // 60)} minutes.")

async def main():
    await client.start(phone_number)
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
