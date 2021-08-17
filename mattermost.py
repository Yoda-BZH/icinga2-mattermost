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
try:
    import urllib.request as urllib_request
except ImportError:
    import urllib2 as urllib_request
try:
    import urllib.parse as urllib_parse
except ImportError:
    import urllib as urllib_parse

# ~ from jinja2 import Environment, FileSystemLoader, select_autoescape
# ~ env = Environment(
    # ~ loader=FileSystemLoader('./'),
    # ~ autoescape=select_autoescape()
# ~ )

VERSION = "1.3.0"

TEMPLATE_HOST_FALLACK = "__{notificationtype}__ {hostalias} is {hoststate} - {hostoutput}"  # noqa
TEMPLATE_SERVICE_FALLBACK = "__{notificationtype}__ {hostalias}/{servicedesc} is {servicestate} - {serviceoutput}" # noqa

def parse():
    parser = argparse.ArgumentParser(description='Sends alerts to Mattermost')
    parser.add_argument('--url', help='Incoming Webhook URL', required=True)
    parser.add_argument('--domain', help="Link to the web interface")
    parser.add_argument('--channel', help='Channel to notify')
    parser.add_argument('--username', help='Username to notify as',
                        default='Icinga')
    parser.add_argument('--iconurl', help='URL of icon to use for username',
                        default='https://s3.amazonaws.com/cloud.ohloh.net/attachments/50631/icinga_logo_med.png') # noqa
    parser.add_argument('--notificationtype', help='Notification Type',
                        required=True)
    parser.add_argument('--hostalias', help='Host Alias', required=True)
    parser.add_argument('--hostobject', help='Host object', required=False)
    parser.add_argument('--hoststate', help='Host State')
    parser.add_argument('--hostoutput', help='Host Output')
    parser.add_argument('--servicedesc', help='Service Description')
    parser.add_argument('--servicestate', help='Service State')
    parser.add_argument('--serviceoutput', help='Service Output')
    parser.add_argument('--serviceicon', help="an icon for the service")
    parser.add_argument('--author', help='Author')
    parser.add_argument('--comment', help='Comment')
    parser.add_argument('--oneline', action='store_true', help='Print only one line')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))
    args = parser.parse_args()
    return args

def emoji(notificationtype):
    return {
        "RECOVERY": ":white_check_mark:",
        #"PROBLEM": ":fire:",
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
    template_fallback = TEMPLATE_SERVICE_FALLBACK if args.servicestate else TEMPLATE_HOST_FALLACK

    template_vars = vars(args)
    template_vars['icon'] = emoji(args.notificationtype)

    if args.oneline:
        text_fallback = text_fallback.splitlines()[0]

    #jinja_name = "service.jinja" if args.servicestate else 'host.jinja'

    #text_markdown = env.get_template(jinja_name).render(**template_vars)
    text_fallback = template_fallback.format(**template_vars)

    if args.author:
        text_fallback += " authored by " + args.author
    if args.comment:
        text_fallback += " commented with " + args.comment

    payload = {
        "username": args.username,
        "icon_url": args.iconurl,
        "attachments": [
            {
                'fallback': text_fallback,
                "color": message_color(args.notificationtype),
                "title:": "foobar",
                #"text": text_markdown,
                "mrkdwn_in": ['text', 'fallback'],
                'author_name': args.author,
                'author_icon': args.author,
                "fields": [
                  {
                    "short": False,
                    "title": args.notificationtype,
                    "value": "{servicedesc} on {hostalias}".format(**template_vars),
                  },
                  {
                    "short": True,
                    "title": "Host",
                    "value": '[{hostobject}]({domain}/monitoring/host/show?host={hostobject})'.format(**template_vars),
                  },
                  {
                    "short": True,
                    "title": "Service",
                    "value": '[{servicedesc}]({domain}/monitoring/service/show?host={hostobject}&service={servicedesc})'.format(**template_vars),
                  },
                ],
            },
        ]
    }
    if args.notificationtype != "RECOVERY":
        payload["attachments"][0]['fields'] += [{
          "short": False,
          "title": "Output",
          "value": '__[{serviceoutput}]({domain}/monitoring/service/show?host={hostobject}&service={servicedesc})__'.format(**template_vars)
        }]

    if args.channel:
        payload["channel"] = args.channel

    data = {'payload' : json.dumps(payload)}
    return data


def request(url, data):
    rawdata = urllib_parse.urlencode(data).encode("utf-8")
    req = urllib_request.Request(url, rawdata)
    response = urllib_request.urlopen(req)
    return response.read()

if __name__ == "__main__":
    args = parse()
    data = make_data(args)
    response = request(args.url, data)
    print(response.decode('utf-8'))
