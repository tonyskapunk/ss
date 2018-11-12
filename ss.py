#!/usr/bin/env python
# TODO: Fix logging/debugging
# TODO: Store results, (sqlite)?
# TODO: Able to re-send emails/sms/whatsapp/telegram/else
# TODO: Add support to telegram: https://python-telegram-bot.org/
# TODO: Turn into a class
# TODO: Add command line args
# TODO: Create package(pip)
# TODO: Able to update wishlist(?)

import sys
import json
import yaml
import random
import logging
import argparse
import datetime
import requests
from os.path import expanduser
from os import getenv

from twilio.rest import Client

_version = "0.5.0"


class SMS:

    def __init__(self, recipients, msg):
        # From twilio.com/console obtain
        # - Account SID
        # - Auth Token
        # - Phone number (twilio.com/console/phone-numbers/incoming)
        # Define environment variables with that information:
        # export TWILIO_SID='AC0123456789abcdef01234567890abcde'
        # export TWILIO_TOKEN='0123456789abcdef0123456789abcdef'
        # export TWILIO_PHONE='+12345678901'
        twilio_account_sid = getenv("TWILIO_SID")
        twilio_token = getenv("TWILIO_TOKEN")
        twilio_phone = getenv("TWILIO_PHONE")
        if not (twilio_account_sid and twilio_token and twilio_phone):
            logger.error("TWILIO Environment value missing")
            sys.exit(1)

        client = Client(twilio_account_sid, twilio_token)

        for recipient in recipients:
            message = client.messages.create(
                to=recipient,
                from_=twilio_phone,
                body=msg
            )
            logger.info(message.sid)


class Participants:
    """Contains all the participants read from a yaml file"""

    def __init__(self, filename):
        # TODO: Check if file exists
        # TODO: Raise errors
        with open(expanduser(filename)) as f:
            y = yaml.load(f)
        f.close()
        self.givers = y


class Notify:
    """Sends notifications through the selected provider/method"""

    def __init__(self, recipients, msg, subject, domain="ss.gift",
                 provider="mailgun"):
        if provider == "mailgun":
            self.mail_mg(recipients, msg, subject, domain)
        pass

    def mail_mg(self, recipients, msg, subject, domain):
        """Sending email through mailgun.
        """
        # Define environment variables with the api key
        # export MAILGUN_KEY='key-1234567890abcdefghijklmnopqrstuvw'
        mg_api_key = getenv("MAILGUN_KEY")
        if not mg_api_key:
            logger.error("MAILGUN_KEY missing")
            return

        sender = "ss@{}".format(domain)
        mg_api_endpoint = "https://api.mailgun.net/v3"
        mg_api_msg = mg_api_endpoint + "/{}/messages".format(domain)
        r = requests.post(
                mg_api_msg,
                auth=('api', mg_api_key),
                data={
                  'from': sender,
                  'to': recipients,
                  'subject': subject,
                  'text': msg,
                },
            )
        if r.ok:
            logger.info('Email to <{}> delivered.'.format(recipients))
        else:
            logger.error('Delivering to: {}.'.format(recipients))
        return


class SecretSanta:
    """Randomizes the picks with a defined logic."""

    def __init__(self, participants, cycle_limit=5):
        self._participants = participants.givers
        self._givers = participants.givers
        self._cycle_limit = cycle_limit
        self._cycle_count = 0
        self._secretsanta_list = []

    @property
    def participants(self):
        return self._participants

    @participants.setter
    def participants(self, new_list):
        self._participants = new_list
        random.shuffle(self._participants)

    @property
    def givers(self):
        return self._givers

    @givers.setter
    def givers(self, participants):
        self._givers = participants.givers
        random.shuffle(self._givers)

    @property
    def cycle_count(self):
        return self._cycle_count

    @property
    def cycle_limit(self):
        return self._cycle_limit

    @property
    def secretsanta_list(self):
        return self._secretsanta_list

    def add_cyclecount(self):
        self._cycle_count += 1

    def get_names(self, participants):
        return [(lambda _x: _x['name'])(_x) for _x in participants]

    def pick(self, giver, available):
        """Randomly picks an available person based on the following logic:
          - No self-picking.
          - No picking up excludes.

        Receives a single participant(giver) to pick from the list of
        available participants.
        """
        # print("Giver: {} | Available: {}".format(
        logger.debug("Giver: {} | Available: {}".format(
               giver['name'],
               self.get_names(available))
              )
        index_picked = random.randrange(len(available))
        picked = available[index_picked]
        logger.debug("Random pick: {}".format(picked['name']))
        # print("Random pick: {}".format(picked['name']))
        if giver['name'] == picked['name']:
            logger.warning('Oops, self-giving...')
            # print('Oops, self-giving...')
            if len(available) == 1:
                return False
            available = available[:index_picked] + available[index_picked+1:]
            picked = self.pick(giver, available)
        elif 'exclude' in giver.keys():
            if picked['name'] in giver['exclude']:
                logger.warning('Oops, attempting to give to an exclusion...')
                # print('Oops, attempting to give to an exclusion...')
                if len(available) == 1:
                    return False
                available = (available[:index_picked]
                             + available[index_picked+1:])
                picked = self.pick(giver, available)
        return picked

    def randomize(self):
        """Randomize the pick"""
        success = False

        # Iterate to obtain the list of givers and receipients
        # The list contains a dictionary with two elements: giver and picked,
        # each one of them is a dictionary with each individual information.
        while not success:
            self._secretsanta_list = []
            logger.debug("--> Run #: {}".format(self.cycle_count))
            # print("--> Run #: {}".format(self.cycle_count))
            if self.cycle_count == self.cycle_limit:
                # print("Reached the limit of attempts({}), exiting..."
                logger.error("Reached the limit of attempts({}), "
                             "exiting...".format(self.cycle_limit))
                break
            available = self.participants
            random.shuffle(available)
            for giver in self.givers:
                picked = self.pick(giver, available)
                if not picked:
                    logger.warning("Can't find a right combo, starting over")
                    # print("Can't find a right combo, starting over")
                    self.add_cyclecount()
                    break
                if len(available) > 1:
                    available = [avail for avail in available
                                 if avail['name'] != picked['name']]
                else:
                    success = True
                self._secretsanta_list.append({"giver": giver,
                                              "picked": picked})
                logger.debug("{} -> {}".format(giver['name'], picked['name']))
                # print("{} -> {}".format(giver['name'], picked['name']))


def main(args):
    """at the moment this reads a yml with data of the users with a predefined
    format(TODO, doc this format)
    Loops until a right random selection has been made or when reached a limit
    of attempts.
    """

    p = Participants(args.filename)
    ss = SecretSanta(p)
    ss.randomize()
    logger.debug("Number of participants: {}".format(len(ss.secretsanta_list)))
    for s in ss.secretsanta_list:
        ts = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())

        wish = "\n- ".join(s['picked']['wish'])
        wish = wish.encode('utf-8')

        msg = '{}\n---\nHola {},\nRegalas a: {}.\nLista:\n- {}\n...\n{}'.format(
            args.subject,
            s['giver']['name'],
            s['picked']['name'],
            wish,
            ts
        )
        logger.debug(msg)

        # SMS
        if 'sms' in s['giver']['notification'].keys():
            sms_recipients = s['giver']['notification']['sms']

            sms = SMS(sms_recipients, msg)

        # Email
        if 'email' in s['giver']['notification'].keys():
            email_recipients = ",".join(s['giver']['notification']['email'])

            email = Notify(email_recipients, msg, args.subject, args.domain)


if __name__ == "__main__":
    # Config logging
    logger = logging.getLogger('ss')
    logger.setLevel(logging.CRITICAL)
    formatter = logging.Formatter(('%(asctime)s [%(name)s] %(levelname)s: '
                                   '%(message)s'))
    ch = logging.StreamHandler()
    ch.setLevel(logging.CRITICAL)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Config parsing
    parser = argparse.ArgumentParser(prog='ss')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(_version))
    parser.add_argument('--verbose', '-v', action='count',
                        help='Increase verbosity, -vvv is debug')
    parser.add_argument('--filename', '-f', required=True)
    parser.add_argument('--subject', '-s', required=True)
    parser.add_argument('--domain', '-d', required=True)
    args = parser.parse_args()
    if args.verbose:
        if args.verbose == 1:
            logger.setLevel(logging.WARNING)
            ch.setLevel(logging.WARNING)
        if args.verbose == 2:
            logger.setLevel(logging.INFO)
            ch.setLevel(logging.INFO)
        if args.verbose >= 3:
            logger.setLevel(logging.DEBUG)
            ch.setLevel(logging.DEBUG)
    main(args)
