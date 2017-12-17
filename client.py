#!/usr/bin/env python3

#############################################################################
#    Client.py - Python 3.2 Pastebin client access.
#    Copyright (C) 2017 entourloop
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

#############################################################################

import argparse
import json
import os

from pastebin import \
    PastebinAPI, \
    PastebinError, \
    PastesParserXML, \
    UsersParser
# PastesParserJSON


def get_creds(path=os.path.join(os.getenv('HOME'), '.pbcreds')):
    """Obtain credentials from the configuration file.
    """

    # TODO Add permissions check (0600), to ensure creds don't stolen easily.
    # TODO Check file existence, check read(), check JSON loading, check keys
    conf_file = open(path, 'r')
    config_str = conf_file.read()
    config = json.loads(config_str)
    return (config['api_dev_key'], config['username'], config['password'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Access and use Pastebin API')
    parser.add_argument('-c', '--config', dest='config',
                        default=os.path.join(os.getenv('HOME'), '.pbcreds'),
                        help='Configuration file path')
    args = parser.parse_args()

    (api_dev_key, username, password) = get_creds(args.config)

    pclient = PastebinAPI(api_dev_key)
    try:
        api_user_key = str(pclient.generate_user_key(username, password))
        # print('API user key: %s' % api_user_key)
    except PastebinError as e:
        print("[-] Pastebin get user key: %s" % e)
    """
    try:
        new_pastie_url = pclient.paste(
            "Hello World!",
            "Hi",
            None,
            False,
            'private',
            '10M')
        print('New pastie URL: %s' % new_pastie_url)
    except PastebinError as e:
        print("[-] Pastebin paste: %s" % e)
    """
    try:
        pastes_list = pclient.list_user_pastes_mdata()
        # print('Pasties for me are: %s' % pastes_list)
    except PastebinError as e:
        print("[-] Pastebin list: %s" % e)

    own_pastes = PastesParserXML.parse(pastes_list)
    if len(own_pastes) < 1:
        print('No pastes available')
        exit(0)
    try:
        priv_paste = pclient.get_user_pastes_content(own_pastes[0].key)
        print('Private paste: %s' % priv_paste.decode('utf-8'))
    except PastebinError as e:
        print("[-] Private paste: %s" % e)
    """
    try:
        raw_paste = PastebinAPI.get_paste(own_pastes[0].key)
        print('Raw paste: %s' % raw_paste.decode('utf-8'))
    except PastebinError as e:
        print("[-] Raw paste: %s" % e)
    try:
        pclient.delete_paste(own_pastes[0].key)
    except PastebinError as e:
        print('[-] Pastebin delete own: %s' % e)
    try:
        pastes_trending = pclient.trending()
        # print('Trending XML is %s' % pastes_trending)
    except PastebinError as e:
        print('[-] Pastebin trending: %s' % e)

    trends = PastesParser.parse(pastes_trending)
    for trend in trends:
        print(trend)
    try:
        pclient.delete_paste(trends[0].key)
    except PastebinError as e:
        print('[-] Pastebin delete trend: %s' % e)
    """
    try:
        own_user = pclient.user_details()
    except PastebinError as e:
        print('[-] Pastebin user details: %s' % own_user)
    # print(own_user)
    users = UsersParser.parse(str(own_user))
    for user in users:
        print(user)
