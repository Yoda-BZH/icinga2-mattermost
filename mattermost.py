#!/usr/bin/env python3

# Copyright (c) 2015 NDrive SA
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse
import json
import sys
import logging
import logging.handlers
import requests

VERSION = "1.3.0"

TEMPLATE_HOST = "__{notificationtype}__ {hostalias} " + \
                "is {hoststate} - {hostoutput}"
TEMPLATE_SERVICE = "__{notificationtype}__ {hostalias}/{servicedesc} " + \
                   "is {servicestate} - {serviceoutput}"

ICONURL = 'https://s3.amazonaws.com/' + \
          'cloud.ohloh.net/attachments/50631/icinga_logo_med.png'

root_log = None

def parse():
    parser = argparse.ArgumentParser(description='Sends alerts to Mattermost')
    parser.add_argument('--url', help='Incoming Webhook URL', required=True)
    parser.add_argument('--domain', help="Link to the web interface")
    parser.add_argument('--channel', help='Channel to notify')
    parser.add_argument('--username', help='Username to notify as',
                        default='Icinga')
    parser.add_argument('--iconurl', help='URL of icon to use for username',
                        default=ICONURL)
    parser.add_argument('--notificationtype', help='Notification Type',
                        required=True)
    parser.add_argument('--hostalias', help='Host Alias', required=True)
    parser.add_argument('--hostobject', help='Host object', required=False)
    parser.add_argument('--hoststate', help='Host State')
    parser.add_argument('--hostoutput', help='Host Output')
    parser.add_argument('--servicedesc', help='Service Description')
    parser.add_argument('--servicestate', help='Service State')
    parser.add_argument('--serviceoutput', help='Service Output')
    parser.add_argument('--serviceicon', help="an icon for the service",
                        default="")
    parser.add_argument('--author', help='Author', default="")
    parser.add_argument('--comment', help='Comment', default="")
    parser.add_argument('--oneline', action='store_true',
                        help='Print only one line')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))
    args = parser.parse_args()

    return args


def emoji(notificationtype):
    return {
        "RECOVERY": ":white_check_mark:",
        # "PROBLEM": ":fire:",
        "PROBLEM": ":stop_sign:",
        "DOWNTIMESTART": ":pause_button:",
        "DOWNTIMEEND": ":arrow_forward:",
        "DOWNTIMEREMOVED": ":record_button:",
        "CUSTOM": ":loop:",
        "FLAPPINGSTART": ":cloud:",
        "FLAPPINGEND": ":sunny:",
        "ACKNOWLEDGEMENT": ":exclamation:",
    }.get(notificationtype, "")


def message_color(notificationtype):
    return {
        "RECOVERY": "#1FD743",
        "PROBLEM": "#D7311F",
        "DOWNTIMESTART": "#000000",
        "DOWNTIMEEND": "#FFFFFF",
        "DOWNTIMEREMOVED": "#FFFFFF",
        "CUSTOM": "#E47529",
        "FLAPPINGSTART": "#E47529",
        "FLAPPINGEND": "#E429A1",
        "ACKNOWLEDGEMENT": "#2976E4",
    }.get(notificationtype, "")


def make_data(args):
    text_template = TEMPLATE_SERVICE if args.servicestate else TEMPLATE_HOST

    # extract all variables from argparse
    template_vars = vars(args)

    # add the icon variable if needed in the template
    template_vars['icon'] = emoji(args.notificationtype)

    # prepare the text fallback, if the full message cannot be display
    # mainly for notification popups
    text_fallback = text_template.format(**template_vars)

    if args.oneline:
        text_fallback = text_fallback.splitlines()[0]

    if args.author:
        text_fallback += " authored by " + args.author
    if args.comment:
        text_fallback += " commented with " + args.comment

    if args.servicestate:
        field_title = '{servicedesc} on {hostalias}'
    else:
        field_title = '{hostalias} is {hoststate}'

    field_host = '[{hostobject}]({domain}/monitoring/host/show?' + \
                 'host={hostobject})'
    field_service = '[{servicedesc}]({domain}/monitoring/service/show?' + \
                    'host={hostobject}&service={servicedesc})'

    payload = {
        "username": args.username,
        "icon_url": args.iconurl,
        "attachments": [
            {
                'fallback': text_fallback,
                "color": message_color(args.notificationtype),
                "title:": "foobar",
                # "text": text_markdown,
                "mrkdwn_in": ['text', 'fallback'],
                'author_name': args.author,
                'author_icon': args.serviceicon,
                "fields": [
                  {
                    "short": False,
                    "title": args.notificationtype,
                    "value": field_title.format(**template_vars),
                  },
                  {
                    "short": True,
                    "title": "Host",
                    "value": field_host.format(**template_vars),
                  },
                ],
            },
        ]
    }

    if args.servicestate:
        payload["attachments"][0]['fields'] += [{
            "short": True,
            "title": "Service",
            "value": field_service.format(**template_vars),
        }]

    # no need for the service message for recoveries
    field_output = '__[{serviceoutput}]({domain}/monitoring/service/show?' + \
                   'host={hostobject}&service={servicedesc})__'
    if args.servicestate and args.notificationtype != "RECOVERY":
        payload["attachments"][0]['fields'] += [{
            "short": False,
            "title": "Output",
            "value": field_output.format(**template_vars)
        }]

    if args.channel:
        payload["channel"] = args.channel

    data = {'payload': json.dumps(payload)}
    root_log.error('mattermost: sending: ' + str(data))

    return data


def request(url, data):
    try:
        # rawdata = urllib_parse.urlencode(data).encode("utf-8")
        # req = urllib_request.Request(url, rawdata)
        # response = urllib_request.urlopen(req)
        #
        # return response.read()

        r = requests.post(url, data)

        return r
    except Exception as e:
        print(e)

        return "error"


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, filename="/tmp/mattermost.log")
    root_log = logging.getLogger('icinga-mattermost')
    log_handler = logging.handlers.SysLogHandler(address="/dev/log")
    root_log.addHandler(log_handler)

    root_log.error('mattermost: sending')
    args = parse()
    root_log.error('mattermost: got args: ' + str(vars(args)))
    data = make_data(args)
    response = request(args.url, data)
    root_log.error('mattermost: got: ' + str(response.text))

    if response.text == "ok":
        sys.exit(0)

    sys.exit(1)
