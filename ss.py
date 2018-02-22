#!/usr/bin/env python
# TODO: Fix logging/debugging
# TODO: Store results, (sqlite)?
# TODO: Able to re-send emails/sms/whatsapp/telegram/else
# TODO: Turn into a class
# TODO: Add command line args
# TODO: Create package(pip)
# TODO: Able to update wishlist(?)

import sys
import yaml
import random
import logging
import argparse
import requests
from os.path import expanduser

_version = "0.1.0"


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

    def __init__(self, provider):
        if provider == "mailgun":
            self.__mg_api_key = ""
            self.domain = "domainname"
            self.sender = "ss@{}".format(domain)
            self.mg_api_endpoint = "https://api.mailgun.net/v3"
            self.mg_api_msg = mg_api_endpoint + "/{}/messages".format(domain)
            self.subject = "secret satan"
            self.text = "{} gives to {}\nwish list:\n{}"

    def mail_mg(self, secrets):
        """Sending email to givers through mailgun.
        """
        for secret in secrets:
            giver = secret['giver']
            picked = secret['picked']
            r = requests.post(
                  self.mg_api_msg,
                  auth=('api', self.__mg_api_key),
                  data={
                    'from': self.sender,
                    'to': giver['notification']['email'],
                    'subject': self.subject,
                    'text': self.text.format(
                              giver['name'],
                              picked['name'],
                              picked['wish'],
                            ),
                  },
                )
            if r.ok:
                logger.info('Email to <{}> delivered.'.
                            format(giver['notification']['email']))
            else:
                logger.error('Delivering to: {}.'.
                             format(giver['notification']['email']))


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
        # logger.debug("Giver: {} | Available: {}".format(
        print("Giver: {} | Available: {}".format(
               giver['name'],
               self.get_names(available))
              )
        index_picked = random.randrange(len(available))
        picked = available[index_picked]
        # logger.debug("Random pick: {}".format(picked['name']))
        print("Random pick: {}".format(picked['name']))
        if giver['name'] == picked['name']:
            # logger.warning('Oops, self-giving...')
            print('Oops, self-giving...')
            if len(available) == 1:
                return False
            available = available[:index_picked] + available[index_picked+1:]
            picked = self.pick(giver, available)
        elif 'exclude' in giver.keys():
            if picked['name'] in giver['exclude']:
                # logger.warning('Oops, attempting to give to an exclusion...')
                print('Oops, attempting to give to an exclusion...')
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
            print("-> Run #: {}".format(self.cycle_count))
            if self.cycle_count == self.cycle_limit:
                # logger.error("Reached the limit of attempts({}), exiting..."
                print("Reached the limit of attempts({}), exiting..."
                      .format(self.cycle_limit)
                      )
                break
            available = self.participants
            random.shuffle(available)
            for giver in self.givers:
                picked = self.pick(giver, available)
                if not picked:
                    # logger.warning("Can't find a right combo, starting over")
                    print("Can't find a right combo, starting over")
                    self.add_cyclecount()
                    break
                if len(available) > 1:
                    available = [avail for avail in available
                                 if avail['name'] != picked['name']]
                else:
                    success = True
                self._secretsanta_list.append({"giver": giver,
                                              "picked": picked})
                # logger.info("{} -> {}".format(giver['name'], picked['name']))
                print("{} -> {}".format(giver['name'], picked['name']))


def main(args):
    """at the moment this reads a yml with data of the users with a predefined
    format(TODO, doc this format)
    Loops until a right random selection has been made or when reached a limit
    of attempts.
    """

    p = Participants(args.filename)
    ss = SecretSanta(p)
    ss.randomize()
    print(ss.secretsanta_list)


if __name__ == "__main__":
    # Config logging
    logger = logging.getLogger('ss')
    logger.setLevel(logging.CRITICAL)
    formatter = logging.Formatter(('%(asctime)s - %(name)s - %(levelname)s - '
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
