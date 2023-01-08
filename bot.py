import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from urllib.parse import urlencode
import database_api_func as db
from database_api_func import DbVkinderUsers as dvu
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from random import randrange
import datetime


class VKinder:
    URL_AUTH = "https://oauth.vk.com/authorize"
    URL_REDIRECT = "https://oauth.vk.com/blank.html"
    URL_USER_PAGE = "https://vk.com/id"
    db_session = None
    vk_session = None
    vk_group_session = None
    user_info = {}

    def __init__(self,
                 my_token: str = None,
                 group_token: str = None,
                 user_id: str = None,
                 db_login: str = None,
                 db_password: str = None,
                 db_name: str = None,
                 db_localhost: int = 5432,
                 app_id=None,
                 group_id=None,
                 users_count_per_inquiry=10,
                 inquiry_counts=0
                 ):
        self.token = my_token
        self.group_token = group_token
        self.user_info["user_id"] = user_id
        self.db_login = db_login
        self.db_password = db_password
        self.db_name = db_name
        self.db_localhost = db_localhost
        self.APP_ID = app_id
        self.GROUP_ID = group_id
        self.users_count_per_inquiry = users_count_per_inquiry
        self.inquiry_counts = inquiry_counts

    def _get_token(self):
        param = {
            "client_id": self.APP_ID,
            "redirect_uri": self.URL_REDIRECT,
            "display": db.DisplayTypes().page,
            "scope": db.ScopeTypes().scope,
            "response_type": "token"
        }
        return "?".join((self.URL_AUTH, urlencode(param)))

    def _set_tokens(self,
                    my_token: str,
                    group_token: str,
                    app_id,
                    group_id
                    ):
        self.token = my_token
        self.group_token = group_token
        self.APP_ID = app_id
        self.GROUP_ID = group_id

    def _set_db_access(self,
                       db_login: str,
                       db_password: str,
                       db_name: str,
                       db_localhost: int
                       ):
        self.db_login = db_login
        self.db_password = db_password
        self.db_name = db_name
        self.db_localhost = db_localhost

    def _database_auth(self):
        DSN = f"postgresql://{self.db_login}:{self.db_password}@localhost:{self.db_localhost}/{self.db_name}"
        engine = sq.create_engine(DSN)

        db.create_tables(engine)

        Session = sessionmaker(bind=engine)
        self.db_session = Session()

    def _authorisation(self):
        print(f"Authorisation info needed. Token URL ==> {self._get_token()}")
        my_token = input("Token to authorize: ")
        app_id = input("Application ID: ")
        group_token = input("Group token: ")
        group_id = input("Group ID: ")
        self._set_tokens(my_token, group_token, app_id, group_id)
        self.vk_session = vk_api.VkApi(token=self.token)
        try:
            self.vk_session.method("users.get")
        except vk_api.AuthError as error_msg:
            print(error_msg)
            return -1
        self.vk_group_session = vk_api.VkApi(token=self.group_token)
        db_login: str = input("Database (PostgresSQL) info needed: \nLogin: ")
        db_password: str = input("Password: ")
        db_name: str = input("Database name: ")
        db_localhost: int = int(input("Database local port (localhost): "))
        self._set_db_access(db_login, db_password, db_name, db_localhost)
        self._database_auth()

    def _set_user_id(self, user_id: str):
        self.user_info["user_id"] = user_id

    def _calculate_age(self, born):
        if born is not None:
            born_day = born[:born.find("."):]
            born_month = born[born.find(".") + 1:born.rfind("."):]
            born_year = born[born.rfind(".") + 1:]
            born = datetime.datetime(int(born_year), int(born_month), int(born_day))
            today = datetime.date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def _get_user_info(self):
        response = self.vk_session.method("users.get",
                                          {"user_ids": self.user_info["user_id"],
                                           "fields": "city, sex, bdate, relation"})
        if response[0].get("city") is not None:
            self.user_info["city"] = response[0].get("city").get("id")
        self.user_info["sex"] = response[0].get("sex")
        self.user_info["relation"] = response[0].get("relation")
        self.user_info["age"] = self._calculate_age(response[0].get("bdate"))

    def _check_user_info(self):
        out = []
        if self.user_info["city"] is None:
            out.append("Город")
        if self.user_info["sex"] is None:
            out.append("Пол")
        if self.user_info["relation"] is None:
            out.append("Семейное положение")
        if self.user_info["age"] is None:
            out.append("Возраст")
        out_str = ','.join(out)
        return out_str if out_str else None

    def _write_msg(self, message: str, event_msg=None, user_id=None):
        if event_msg is not None:
            self.vk_group_session.method('messages.send',
                                         {'message': message,
                                          'peer_id': event_msg.peer_id,
                                          'random_id': randrange(10 ** 7)})

        elif user_id is not None:
            self.vk_group_session.method('messages.send',
                                         {'user_id': user_id,
                                          'message': message,
                                          'random_id': randrange(10 ** 7)})
        else:
            print("No event and no user_id to send message!")

    def _get_users(self):
        response_users = self.vk_session.method("users.search",
                                                {"sort": 0,
                                                 "offset": self.inquiry_counts * self.users_count_per_inquiry,
                                                 "count": self.users_count_per_inquiry,
                                                 "fields": "city, sex, bdate, relation",
                                                 "city": self.user_info["city"],
                                                 "sex": 1 if self.user_info["sex"] == 2 else 2,
                                                 "status": self.user_info["relation"] if (
                                                         self.user_info["relation"] == 1 or
                                                         self.user_info["relation"] == 6) else 6,
                                                 "age_from": int(self.user_info["age"]) - 5 if int(
                                                     self.user_info["age"]) - 5 >= 0 else 0,
                                                 "age_to": int(self.user_info["age"]) + 5})
        return response_users["items"]

    def _rating_count(self, user):
        rating = 0
        if user.get("city") is not None:
            if user.get("city").get("id") == self.user_info["city"]:
                rating += 2
        if self._calculate_age(user.get("bdate")) in range(self.user_info["age"] - 5, self.user_info["age"] + 5):
            rating += 2
        if user.get("sex") == 1 if self.user_info["sex"] == 2 else 2:
            rating += 2
        if user.get("relation") == self.user_info["relation"] if (
                                                         self.user_info["relation"] == 1 or
                                                         self.user_info["relation"] == 6) else 6:
            rating += 2
        return rating

    def _photos_url(self, photo_list, event):
        for photo  in photo_list:
            url = photo["sizes"][3]["url"]
            self._write_msg(f"Фотография: {url}", event_msg=event.message)

    def _user_info_output(self, user, event):
        self._write_msg(f"Фотографии пользователя {user.vk_id}:", event_msg=event.message)
        response_photo = self.vk_session.method("photos.get",
                               {"owner_id": user.vk_id,
                                "extended": 1,
                                "feed_type": "photo",
                                "photo_sizes": 1,
                                "rev": 1,
                                "album_id": "profile"})
        if response_photo["count"] == 0:
            db.update_user_db(session=self.db_session, vk_id=user.vk_id, rating=user.rating-1, viewed=True)
            return
        else:
            if response_photo["count"] <= 3:
                self._photos_url(response_photo["items"], event)
            else:
                response_photo["items"].sort(key=lambda key: int(key["likes"]["count"]))
                photo_list = [response_photo["items"][-1],response_photo["items"][-2],response_photo["items"][-3]]
                self._photos_url(photo_list, event)

        self._write_msg(f"Страница пользователя {user.vk_id}:", event_msg=event.message)
        self._write_msg(self.URL_USER_PAGE + str(user.vk_id), event_msg=event.message)
        db.update_user_db(session=self.db_session, vk_id=user.vk_id, rating=user.rating, viewed=True)

    def _bot_main_work(self, event):
        users_list = self._get_users()

        for user in users_list:
            db.add_user_db(self.db_session, user["id"], self._rating_count(user))

        for user in self.db_session.query(dvu).filter(dvu.viewed == False).filter(dvu.rating > 7).all():
            self._user_info_output(user, event)


    def bot_dialogue(self):
        self._authorisation()
        input_data_flag = False
        longpoll = VkBotLongPoll(self.vk_group_session, self.GROUP_ID)
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.message.text == "Стоп!":
                    self._write_msg("До свидания!", event_msg=event.message)
                    break
                else:
                    if not input_data_flag:
                        if event.message.text == "Начать" or event.message.text == "Start":
                            self._write_msg("Привет! Я - Бот VKinder!\n "
                                            "Я буду искать в пару подходящих по возрасту, местоположению, полу и "
                                            "семейному положению людей для указанного тобой человека!\n "
                                            "Для того чтобы прекратить работу бота введи \"Стоп!\"\n"
                                            "Для сброса поиска сначала убедись что "
                                            "ты не дозаполняешь данные о пользователе"
                                            "(напиши все недостающие данные) после чего снова напиши \"Начать\""
                                            "Для выведения дополнительных результатов поиска набери \"Дальше\""
                                            "(выводится по 10 пользователей)"
                                            "А теперь скажи, для кого мы ищем пару или напиши "
                                            "\"Себе\" если ищешь пару для себя. "
                                            "(ID только число):",
                                            event_msg=event.message)
                            self.user_info.clear()
                            self.user_info = dict.fromkeys(["user_id", "city", "sex", "relation", "age"])
                            self.inquiry_counts = 0
                            self._database_auth()
                        elif event.message.text == "Себе" or event.message.text == "Self":
                            self._set_user_id(event.message.from_id)
                            self._get_user_info()
                            if self._check_user_info() is None:
                                self._bot_main_work(event)
                            else:
                                self._write_msg(
                                    f"У человека, для которого мы ищем пару не хватает в профиле информации: "
                                    f"{self._check_user_info()} \n"
                                    f"Поэтому давай введем их вручную в формате "
                                    f"(по одному сообщению на параметр поиска):\n"
                                    f"\"Город: ...\"\n "
                                    f"\"Возраст: ...(число)\"\n"
                                    f"\"Пол: ...(1 — женский,2 — мужской)\"\n "
                                    f"\"Семейное положение: ...(1 - не женат/не замужем,2 — есть друг/есть подруга,"
                                    f"3 — помолвлен/помолвлена,4 — женат/замужем,5 — всё сложно,6 — в активном поиске,"
                                    f"7 — влюблён/влюблена,8 — в гражданском браке)\"\n",
                                    event_msg=event.message)
                                input_data_flag = True
                        elif event.message.text.isdigit():
                            self._set_user_id(event.message.text)
                            self._get_user_info()
                            if self._check_user_info() is None:
                                self._bot_main_work(event)
                            else:
                                self._write_msg(
                                    f"У человека, для которого мы ищем пару не хватает в профиле информации: "
                                    f"{self._check_user_info()} \n"
                                    f"Поэтому давай введем их вручную в формате "
                                    f"(по одному сообщению на параметр поиска):\n"
                                    f"\"Город: ...\"\n "
                                    f"\"Возраст: ...(число)\"\n"
                                    f"\"Пол: ...(1 — женский,2 — мужской)\"\n "
                                    f"\"Семейное положение: ...(1 - не женат/не замужем,2 — есть друг/есть подруга,"
                                    f"3 — помолвлен/помолвлена,4 — женат/замужем,5 — всё сложно,6 — в активном поиске,"
                                    f"7 — влюблён/влюблена,8 — в гражданском браке)\"\n",
                                    event_msg=event.message)
                                input_data_flag = True
                        elif event.message.text == "Дальше" or event.message.text == "Next":
                            if self._check_user_info() is None:
                                self.inquiry_counts += 1
                                self._bot_main_work(event)
                    else:
                        city_check = event.message.text.find("Город")
                        age_check = event.message.text.find("Возраст")
                        sex_check = event.message.text.find("Пол")
                        relation_check = event.message.text.find("Семейное положение")

                        if city_check != -1:
                            response_city = self.vk_session.method(
                                "database.getCities",
                                {"q": event.message.text[event.message.text.find(":") + 2:],
                                 "need_all": 1,
                                 "count": 1})
                            self.user_info["city"] = response_city["items"][0]["id"]
                        if age_check != -1:
                            if event.message.text[event.message.text.find(":") + 2:].isdidgit():
                                self.user_info["age"] = int(event.message.text[
                                                    event.message.text.find(":") + 2:])
                        if sex_check != -1:
                            self.user_info["sex"] = event.message.text[
                                                       event.message.text.find(":") + 2:]
                        if relation_check != -1:
                            self.user_info["relation"] = event.message.text[
                                                         event.message.text.find(":") + 2:]
                        if self._check_user_info() is None:
                            input_data_flag = False
                            self._bot_main_work(event)

    # Tried to take token automatically (didn't make it after all)
    # def get_token_authorization_vk(self):
    #     login_vk = input("Login VK: ")
    #     password_vk = input("Password VK: ")
    #
    #     driver = webdriver.Chrome(
    #         executable_path=r'/chromedriver'
    #     )
    #     driver.get(self.get_token())
    #
    #     # XPath form authorization
    #     username = '//*[@id="login_submit"]/div/div/input[6]'
    #     password = '//*[@id="login_submit"]/div/div/input[7]'
    #     login = '//*[@id="install_allow"]'
    #     # login / password input
    #     driver.find_element_by_xpath(username).send_keys(login_vk)
    #     driver.find_element_by_xpath(password).send_keys(password_vk)
    #     driver.find_element_by_xpath(login).click()
    #
    #     answer = driver.current_url
    #
    def __del__(self):
        self.db_session.close()


def bot_vkinder():
    client = VKinder()
    client.bot_dialogue()
