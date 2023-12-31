####################
# custom insta bot #
####################
from argparse import ArgumentParser
from glob import glob
from os.path import expanduser
import os
from platform import system
from sqlite3 import OperationalError, connect
from datetime import datetime

import json
import yaml

try:
    from instaloader import ConnectionException, Instaloader, Profile
except ModuleNotFoundError:
    raise SystemExit("Instaloader not found.\n  pip install [--user] instaloader")

use_session_file = True
session_file_already_exists = True


# class
class CustomInstaLoader:

    # the init method
    def __init__(self):
        self.instaloader = Instaloader(max_connection_attempts=1)
        print('new instabot object created')
        self.creds = None

        with open('creds.yml', 'r') as stream:
            try:
                # Converts yaml document to python object
                self.creds = yaml.safe_load(stream)
                # Printing dictionary
                print(self.creds)
            except yaml.YAMLError as e:
                print(e)
                return

    def check_followers(self, user_name=None):
        if not user_name:
            user_name = self.creds['user']
        profile = Profile.from_username(self.instaloader.context, user_name)
        print(f'Follower count for {user_name}: {profile.followers}')

        my_followers = profile.get_followers()
        list_of_followers = []
        for follower in my_followers:
            follower_username = follower.username
            list_of_followers.append(follower_username)
        print(f"List of {user_name}'s followers: \n{list_of_followers}")

        try:
            # compare difference from last time
            list_of_files = glob('database/*')  # * means all if need specific format then *.csv
            latest_file = max(list_of_files, key=os.path.getctime)
            with open(latest_file, 'r') as openfile:
                last_save = json.load(openfile)
                prev_list_of_followers = last_save[user_name]['followers']

                # check for lost followers
                difference_list = []
                for user in prev_list_of_followers:
                    if user not in list_of_followers:
                        difference_list.append(user)
                print(f'list of lost followers: {difference_list}')

                # check for new followers
                difference_list = []
                for user in list_of_followers:
                    if user not in prev_list_of_followers:
                        difference_list.append(user)
                print(f'list of gained followers: {difference_list}')

        except Exception as error:
            print('no previously saved follower database files found!')

        dict_obj = {user_name: {}}
        dict_obj[user_name]['followers'] = list_of_followers
        dict_obj[user_name]['follower_count'] = profile.followers

        # Serializing json
        json_object = json.dumps(dict_obj, indent=4)

        current_date = datetime.today().strftime('%Y-%m-%d %H-%M-%S')
        # Writing to sample.json
        with open(f"database/follower_db-{current_date}.json", "w") as outfile:
            outfile.write(json_object)

    def login(self):
        print('attempting login to insta servers')
        # first try to log in with session file saved
        failed_session_load = False
        try:
            self.instaloader.load_session_from_file(self.creds['user'], self.creds['session_file'])
            username = self.instaloader.test_login()
            print(f'Logged into {username} with pre-existing session file')
        except Exception as error:
            print('Failed to login with existing session file')
            print(error)
            failed_session_load = True

        if failed_session_load:
            # then try to get cookies from FireFox
            failed_session_load = False
            try:
                cookie_files = self.get_cookiefile()
                cookie_data = self.import_session(cookie_files)
                self.instaloader.context._session.cookies.update(cookie_data)  # this makes the bot use the cookie data
                # for authenticating its requests from now on
                self.instaloader.save_session_to_file(self.creds['session_file'])  # now save it for next time...

                username = self.instaloader.test_login()
                if not username:
                    failed_session_load = True
                print("Imported session cookie for {}.".format(username))
                self.instaloader.context.username = username

            except Exception as error:
                failed_session_load = True
                print(error)

            if failed_session_load:
                print("Not logged in. Are you logged in successfully in Firefox?")

    def get_cookiefile(self):
        default_cookiefile = {
            "Windows": "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite",
            "Darwin": "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
        }.get(system(), "~/.mozilla/firefox/*/cookies.sqlite")
        cookiefiles = glob(expanduser(default_cookiefile))
        if not cookiefiles:
            raise SystemExit("No Firefox cookies.sqlite file found. Use -c COOKIEFILE.")
        return cookiefiles[0]

    def import_session(self, cookiefile):
        print("Using cookies from {}.".format(cookiefile))
        conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
        try:
            cookie_data = conn.execute(
                "SELECT name, value FROM moz_cookies WHERE baseDomain='instagram.com'"
            )
        except OperationalError:
            cookie_data = conn.execute(
                "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
            )

        return cookie_data


if __name__ == '__main__':
    my_insta_bot = CustomInstaLoader()
    my_insta_bot.login()
    my_insta_bot.check_followers()

