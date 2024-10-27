import telegram
import asyncio
from pathlib import Path
import zipfile
import os
import datetime
import logging
from configparser import ConfigParser

class TELEGRAMBOT:
    def __init__(self):
        self.api = "" # you'r api key
        self.lms_url = "https://lms.kluniversity.in/login/index.php"

        r = telegram.request.HTTPXRequest(connection_pool_size=1_000, pool_timeout=10_000)
        self.bot = telegram.Bot(token = self.api, request=r)

        self.files_folder = Path("") # your folder path
        self.offset = None

        self.config = ConfigParser()
        self.config_file_path = "./telegram_config_file.ini"
        if Path(self.config_file_path).exists():
            self.config.read(self.config_file_path)
        else:
            with open(self.config_file_path,"a") as f:
                pass

        self.logger = logging.Logger(name="Telegram Bot",level=logging.DEBUG)
        self.errors_file_path = "./errors.txt"
        self.foramater = logging.Formatter(fmt="Time: %(asctime)s, MSG: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        self.file_handeler = logging.FileHandler(filename=self.errors_file_path, mode="a", encoding="utf-8")
        self.file_handeler.setFormatter(fmt=self.foramater)
        self.logger.addHandler(hdlr=self.file_handeler)
    
        self.scheduled_times = ["18:06:08","20:06:08","22:06:15"]
        self.scheduled_times_bool = [False,False,False]
        self.is_wake_up_time_completed = False
        self.current_date = str((datetime.datetime.now() + datetime.timedelta(days=0,hours=3,minutes=30)).date())

        self.max_days_idle = 10

    async def update_my_bot(self):
        try:
            return await self.bot.get_updates(offset=self.offset)
        except Exception as e:
            return ()

    async def main(self):
        while True:
            data_list = await self.update_my_bot()
            self.current_date_time = (datetime.datetime.now() + datetime.timedelta(days=0,hours=3,minutes=30))
    
            tasks = []
            for data in data_list:
                try:
                    callback_data = data.callback_query.data
                    user_id = str(data.callback_query.from_user.id)
                    last_update_id = data.update_id
                    user_name = data.callback_query.from_user.username
                    first_name = data.callback_query.from_user.first_name
                except:
                    if not data.message:
                        continue

                    user_id = str(data.message.from_user.id)
                    last_update_id = data.update_id
                    user_name = data.message.from_user.username
                    callback_data = None
                    first_name = data.message.from_user.first_name
                                
                if self.offset != last_update_id:

                    if not self.config.has_section(section=str(user_id)):
                        self.config.add_section(section=str(user_id))
                        self.config[str(user_id)] = {"last_update_id":str(last_update_id), "my_dict":'{}',
                                                    "my_dict_path":'{}', "current_path":"None",
                                                    "user_name":str(user_name), "last_chat_date":str(self.current_date),
                                                    "first_name":"None","is_notifications_enabled":"True"}
                        
                        self.update_config_file(mode='a')
                    
                    
                    self.config.set(section=str(user_id), option="last_update_id", value=str(last_update_id))
                    self.config.set(section=str(user_id), option="last_chat_date", value=str(self.current_date_time.strftime("%Y-%m-%d")))
                    self.config.set(section=str(user_id), option="user_name", value=str(user_name)) # ever times updates user name
                    self.config.set(section=str(user_id), option="first_name", value=str(first_name)) # ever times updates first name
                    self.update_config_file(mode='w')

                    self.offset = last_update_id

                    task = asyncio.create_task(self.bot_reply(data=data, telegram_user_id=user_id, callback_data=callback_data))
                    tasks.append(task)
                    
            await asyncio.gather(*tasks)
            
            h1,m1,s1 = self.current_date_time.strftime("%H:%M:%S").split(":")
            if h1 == "06" and (m1 in ["00","01","02"]) and not self.is_wake_up_time_completed:
                self.is_wake_up_time_completed = True

                await self.send_wake_up_message_to_all_users(telegram_user_ids=list(self.config.sections()))

            if str(self.current_date_time.date()) != self.current_date:
                self.current_date = str(self.current_date_time.date())
                self.scheduled_times_bool = [False] * len(self.scheduled_times)
                self.is_wake_up_time_completed = False

            for i,times in enumerate(self.scheduled_times):
                h2,m2,s2 = map(int,times.split(":"))

                x = (datetime.timedelta(hours=h2,minutes=m2,seconds=s2) - datetime.timedelta(hours=int(h1),minutes=int(m1),seconds=int(s1)))

                h,m,s = str(x).split(":")
                try:
                    h = int(h)
                    m = int(m)
                except:
                    pass
                
                if x.days == 0 and  not self.scheduled_times_bool[i] and h == 0 and m <= 5:
                    self.scheduled_times_bool[i] = True
                    messages = ["Time To Check Out The LMS",self.lms_url,"LogIn Now To Check Updates...","To Stop Updates Use command end"]
                    await self.send_message_to_all_users(telegram_user_ids=list(self.config.sections()), messages=messages, error_name=" LMS ", is_informational=False)
            
            with open("./information.txt","r+") as f:
                information_lines = f.read().splitlines()
                if information_lines != []:
                    await self.send_message_to_all_users(telegram_user_ids=list(self.config.sections()), messages=information_lines, error_name=" Information ", is_informational=True)

                f.truncate(0) # remove the entire data

            await asyncio.sleep(1)
    
    def update_config_file(self,mode:str):

        with open(self.config_file_path, mode) as f:
            self.config.write(f)

    async def send_message_to_all_users(self, telegram_user_ids:list, messages:list[str], error_name:str, is_informational:bool):
        
        try:
            if telegram_user_ids:
                telegram_user_id:str = telegram_user_ids[0]
                if self.config.get(section=telegram_user_id, option="is_notifications_enabled") == "True" or is_informational:
                    for message in messages:
                        await self.bot.send_message(chat_id=telegram_user_id, text=message)
            
                telegram_user_ids.pop(0)
                await self.send_message_to_all_users(telegram_user_ids=telegram_user_ids, messages=messages, error_name=error_name, is_informational=is_informational)
        except Exception as e:
            
            msg = str(self.current_date_time) + error_name + str(self.config.get(section=telegram_user_id, option="user_name"))
            msg += "->" + str(e) + "\n"
            self.logger.info(msg=msg)

            self.config.remove_section(section=telegram_user_id) # deletes the user from saved dictionary
            self.update_config_file(mode="w")

            telegram_user_ids.pop(0)
            await self.send_message_to_all_users(telegram_user_ids=telegram_user_ids, messages=messages, error_name=error_name, is_informational=is_informational)
    
    async def send_wake_up_message_to_all_users(self, telegram_user_ids:list):
        try:
            if telegram_user_ids:
                telegram_user_id:str = telegram_user_ids[0]

                y1,m1,d1 = map(int,self.config.get(section=telegram_user_id, option="last_chat_date").split("-"))
                y2,m2,d2 = map(int,self.current_date.split("-"))

                if (datetime.datetime(year=y2,month=m2,day=d2) - datetime.datetime(year=y1,month=m1,day=d1)).days >= self.max_days_idle:
                    await self.bot.send_message(chat_id=telegram_user_id, text=f"Since You chat a long back on {self.config.get(section=telegram_user_id, option="last_chat_date")}")
                    await self.bot.send_message(chat_id=telegram_user_id, text="From now onward's no update's will come")
                    await self.bot.send_message(chat_id=telegram_user_id, text="To Again Get Updates use Command start")
                    self.config.remove_section(section=telegram_user_id)
                    self.update_config_file(mode="w")

                else:
                    if self.config.get(section=telegram_user_id, option="is_notifications_enabled") == "True":
                        user_name_saved_in_file = self.config.get(section=telegram_user_id, option="user_name")
                        if user_name_saved_in_file == "None":
                            first_name_saved_in_file = self.config.get(section=telegram_user_id, option="first_name")
                            await self.bot.send_message(chat_id=telegram_user_id, text=f"Good Morning {first_name_saved_in_file}")
                            await self.bot.send_message(chat_id=telegram_user_id, text="Hurry! Time To Wake Up It's 6:00 AM")
                            await self.bot.send_message(chat_id=telegram_user_id, text="You'r username is set None please update your username")
                        else:
                            await self.bot.send_message(chat_id=telegram_user_id, text=f"Good Morning {user_name_saved_in_file}")
                            await self.bot.send_message(chat_id=telegram_user_id, text="Hurry! Time To Wake Up It's 6:00 AM")

                telegram_user_ids.pop(0)
                await self.send_wake_up_message_to_all_users(telegram_user_ids)
        except Exception as e:
            msg = str(self.current_date_time) + " wake up " + str(self.config.get(section=telegram_user_id, option="user_name"))
            msg += "->" + str(e) + "\n"
            self.logger.info(msg=msg)

            self.config.remove_section(section=telegram_user_id) # deletes the user from saved dictionary
            self.update_config_file(mode="w")

            telegram_user_ids.pop(0)
            await self.send_wake_up_message_to_all_users(telegram_user_ids)



    def get_files_in_folder(self, path, telegram_user_id):

        self.current_path:Path = Path(path)

        self.config.set(section=str(telegram_user_id), option="my_dict", value="{}")
        self.config.set(section=str(telegram_user_id), option="my_dict_path", value="{}")
        self.config.set(section=str(telegram_user_id), option="current_path", value=str(self.current_path))
        self.update_config_file(mode="w")

        counter = 1
        d1_file_names = {}
        d2_file_paths = {}
        for file in Path(path).iterdir():

            d1_file_names[str(counter)] = file.name
            d2_file_paths[str(counter)] = file.as_posix()

            counter += 1
        
        for file in Path(path).iterdir():
            if file.is_dir():
                d1_file_names[str(counter)] = f"Download {file.stem} zip"
                d2_file_paths[str(counter)] = file.as_posix()
                counter += 1

        if Path(path).as_posix() != self.files_folder.as_posix():
            d1_file_names[str(counter)] = "Back..."

        self.config.set(section=str(telegram_user_id), option="my_dict", value=str(d1_file_names))
        self.config.set(section=str(telegram_user_id), option="my_dict_path", value=str(d2_file_paths))
        self.update_config_file(mode="w")
    
        buttons = []
        row = []
        button_counter = 0
        for key,value in dict(eval((self.config.get(section=str(telegram_user_id), option="my_dict")))).items():
            
            if button_counter == 2: # for each row two buttons
                button_counter = 0
                buttons.append(row)
                row = []
                
            row.append(telegram.InlineKeyboardButton(text=value, callback_data=key))
            button_counter += 1
        
        if row: # if any extra row 
            buttons.append(row)
        
        return telegram.InlineKeyboardMarkup(inline_keyboard=buttons)
    
        
    async def bot_reply(self, data:telegram._update.Update, telegram_user_id, callback_data):
        
        try:
            if callback_data:
                chat_id = data.callback_query.message.chat.id
                message_sent = str(callback_data)
                full_name = data.callback_query.message.chat.username
                saved_dict_data:dict = dict(eval((self.config.get(section=str(telegram_user_id), option="my_dict"))))
        
                d = {}
                for both_keys in data.callback_query.message.reply_markup.inline_keyboard:
                    for each_key in both_keys:
                        each_key:telegram.InlineKeyboardButton = each_key
                        d[each_key.callback_data] = each_key.text
                
                if d != saved_dict_data:
                    # this is for the when ever the user selected the previous menu item or the user entered
                    # the key number in message box the message sent changes to the key no in the dictionary
                    # so it was invalid then the same menu returns back
                    # message may be any thing but not numbers for understanding i wrote the same message
                    message_sent = "No selected the updated menu or user enter the key number not in the dictionary"
            
            else:
                chat_id = data.message.chat.id
                message_sent = None # default message sent is None
                message_sent = data.message.text.lower()
                full_name = data.message.chat.username

        except Exception as e:
            msg = str(self.current_date_time) + " bot reply " + "\n" + str(data) + "\n"
            msg += str(message_sent) + "->" + str(self.config.get(section=str(telegram_user_id), option="user_name")) + "->" + str(e) + "\n"

            self.logger.info(msg=msg)
            return
        if message_sent in ("hello","hi"):
            await self.bot.send_message(chat_id=chat_id, text=f"Hello {full_name} Welcome !\n send start to start")
        
        elif message_sent in ("/start","start","st"):
            mark_up = self.get_files_in_folder(path=self.files_folder, telegram_user_id=telegram_user_id)

            self.config.set(section=telegram_user_id, option="is_notifications_enabled", value="True")
            self.update_config_file(mode="w")
 
            await self.bot.send_message(chat_id=chat_id, text="Navigation Menu", reply_markup=mark_up)

        elif message_sent in ("logout","close","end","shutdown","thanks","thank you","bye","/end"):
            await self.bot.send_message(chat_id=chat_id, text=f"{full_name} Have a nice day!")
            await self.bot.send_message(chat_id=chat_id, text="Bye!")
            await self.bot.send_message(chat_id=chat_id, text="To Again Get Updates use Command start")

            self.config.set(section=telegram_user_id, option="is_notifications_enabled", value="False")
            self.config.set(section=telegram_user_id, option="my_dict", value="{}")
            self.config.set(section=telegram_user_id, option="my_dict_path", value="{}")
            self.config.set(section=telegram_user_id, option="current_path", value="None")
            self.update_config_file(mode="w")

            return

        elif self.config.has_section(section=str(telegram_user_id)) and dict(eval((self.config.get(section=str(telegram_user_id), option="my_dict")))):

            my_dict:dict = dict(eval((self.config.get(section=str(telegram_user_id), option="my_dict"))))
            my_dict_paths:dict = dict(eval((self.config.get(section=str(telegram_user_id), option="my_dict_path"))))

            if message_sent not in my_dict:
                await self.bot.send_message(chat_id=chat_id, text="Invalid option")
                current_path:Path = Path(self.config.get(section=str(telegram_user_id), option="current_path"))
                mark_up = self.get_files_in_folder(path=current_path, telegram_user_id=telegram_user_id)
                await self.bot.send_message(chat_id=chat_id, text="Select Among The Options Only", reply_markup=mark_up)

            elif "zip" in my_dict[message_sent]:
                path = my_dict_paths[message_sent]
                
                if Path(f"./{telegram_user_id}.zip").exists():
                    await self.delete_zip_file(telegram_user_id=telegram_user_id)
                
                try:
                    await self.create_zip_folder(path=path, telegram_user_id=telegram_user_id)
                    await self.send_zip_file(chatid = chat_id)
                except Exception as e:
                    await self.bot.send_message(chat_id=chat_id, text=f"Error creating zip file: {str(e)}")
                    current_path:Path = Path(self.config.get(section=str(telegram_user_id), option="current_path"))
                    mark_up = self.get_files_in_folder(path=current_path, telegram_user_id=telegram_user_id)
                    await self.bot.send_message(chat_id=chat_id, text="Please Select Again", reply_markup=mark_up)


            elif "Back" in my_dict[message_sent]:
                current_path:Path = Path(self.config.get(section=str(telegram_user_id), option="current_path"))
                mark_up = self.get_files_in_folder(path=current_path.parent, telegram_user_id=telegram_user_id)
                await self.bot.send_message(chat_id=chat_id, text="Backed Up Menu", reply_markup=mark_up)

            elif Path(my_dict_paths[message_sent]).is_file():
                try:
                    await self.bot.send_document(chat_id=chat_id, document=my_dict_paths[message_sent], caption="Complete Early And Submit")
                except Exception as e:
                    await self.bot.send_message(chat_id=chat_id, text=f"Error Sending Document: {str(e)}")
                    current_path:Path = Path(self.config.get(section=str(telegram_user_id), option="current_path"))
                    mark_up = self.get_files_in_folder(path=current_path, telegram_user_id=telegram_user_id)
                    await self.bot.send_message(chat_id=chat_id, text="Please Select Again", reply_markup=mark_up)

            elif Path(my_dict_paths[message_sent]).is_dir():
                mark_up = self.get_files_in_folder(path=my_dict_paths[message_sent], telegram_user_id=telegram_user_id)
                await self.bot.send_message(chat_id=chat_id, text="In Directory Menu", reply_markup=mark_up)

        else:
            with open ("./empty.txt" ,"a") as fo:
                fo.write(str(self.current_date_time) + "->" + str(message_sent)+ "->" + str(self.config.get(section=str(telegram_user_id), option="user_name")) + "\n" ) 

            await self.bot.send_message(chat_id=chat_id, text="Sorry I can't understand I am in still learning stage")
            await self.bot.send_message(chat_id=chat_id, text="For getting file's send start message")
    
    async def create_zip_folder(self, path, telegram_user_id):
        main_parts = len(Path(path).parts)
        des_path = "./" + str(telegram_user_id) + ".zip"

        with zipfile.ZipFile(file=des_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in Path(path).walk():
                for file in files:
                    x = "/".join(Path(root, file).parts[main_parts::])
                    zipf.write(filename=Path(root, file), arcname=x)
        

    async def send_zip_file(self, chatid):
        await self.bot.send_document(chat_id=chatid, document=f"./{chatid}.zip", caption="Thank's for using Bot!")
        await self.delete_zip_file(telegram_user_id = chatid)
       
    async def delete_zip_file(self, telegram_user_id):
        path = f"./{telegram_user_id}.zip"
        os.remove(path)
    
if __name__ == "__main__":
    try:
        asyncio.run(TELEGRAMBOT().main())
    except Exception as e:
        with open ("./errors.txt", "a") as fo:
            d = datetime.datetime.now() + datetime.timedelta(days=0, hours=2, minutes=30)
            fo.write(str(d) + " Main function ")
            fo.write(str(e) + "\n")
