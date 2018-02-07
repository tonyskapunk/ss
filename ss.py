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

_version = 0.0.1

mg_api_key = ""
domain = "domainname"
sender = "ss@{}".format(domain)
mg_api_endpoint = "https://api.mailgun.net/v3"
mg_api_msg = mg_api_endpoint + "/{}/messages".format(domain)
subject = "secret satan"
text = "{} gives to {}\nwish list:\n{}"


def mail_mg(secrets):
    """Sending email to givers through mailgun.
    """
    for secret in secrets:
        giver = secret['giver']
        picked = secret['picked']
        r = requests.post(
              mg_api_msg,
              auth=('api', mg_api_key),
              data={
                'from': sender,
                'to': giver['email'],
                'subject': subject,
                'text': text.format(
                          giver['name'],
                          picked['name'],
                          picked['wish'],
                        ),
              },
            )
        if r.ok:
            logger.info('Email to <{}> delivered.'.format(email))
        else:
            logger.error('Delivering to: {}.'.format(email))


def pick(giver, available):
    """Randomly picks a person based on the following logic
    - No self-picking.
    - No picking up parents.
    """
    logger.debug("Giver: {} | Available: {}".format(
          giver['name'], [(lambda _x: _x['name'])(_x) for _x in available]))
    index_picked = random.randrange(len(available))
    picked = available[index_picked]
    logger.debug("Random pick: {}".format(picked['name']))
    if giver['name'] == picked['name']:
        logger.warning('Oops, self-giving...')
        if len(available) == 1:
            return False
        picked = pick(giver,
                      available[:index_picked]+available[index_picked+1:])
    elif 'parents' in giver.keys():
        if picked['name'] in giver['parents']:
            logger.warning('Oops, kiddo giving to parent..')
            if len(available) == 1:
                return False
            picked = pick(giver,
                          available[:index_picked]+available[index_picked+1:])
    return picked


def main(args):
    """at the moment this reads a yml with data of the users with a predefined
    format(TODO, doc this format)
    Loops until a right random selection has been made or when reached a limit
    of attempts.
    """
    with open(args.filename) as f:
        y = yaml.load(f)
    f.close()

    givers = y
    random.shuffle(givers)
    success = False
    cycle_limit = 5
    cycle = 0

    # Iterate to obtain the list of givers and receipients
    # The list contains a dictionary with two elements: giver and picked,
    # each one of them is a dictionary with each individual information.
    while not success:
        if cycle == cycle_limit:
            logger.error("Reached the limit of attempts({}), exiting..."
                         .format(cycle_limit)
                         )
            break
        available = y
        random.shuffle(available)
        ss = []
        for giver in givers:
            picked = pick(giver, available)
            if not picked:
                logger.warning("Can't find a right combo, starting over")
                cycle += 1
                break
            if len(available) > 1:
                available = [avail for avail in available
                             if avail['name'] != picked['name']]
            else:
                success = True
            ss.append({"giver": giver, "picked": picked})
            logger.info("{} -> {}\n".format(giver['name'], picked['name']))


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
