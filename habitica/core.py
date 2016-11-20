#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Phil Adams http://philadams.net

habitica: commandline interface for http://habitica.com
http://github.com/philadams/habitica

TODO:philadams add logging to .api
TODO:philadams get logger named, like requests!
"""


from bisect import bisect
import logging
import os.path
from time import sleep
from webbrowser import open_new_tab
import itertools
from docopt import docopt
from . import api
import json
from pprint import pprint

try:
    import ConfigParser as configparser
except:
    import configparser

RED = "\033[91m"
GREEN = "\033[92m"
VERSION = 'habitica version 0.0.13'
TASK_VALUE_BASE = 0.9747  # http://habitica.wikia.com/wiki/Task_Value
HABITICA_REQUEST_WAIT_TIME = 0.5  # time to pause between concurrent requests
HABITICA_TASKS_PAGE = '/#/tasks'
# https://trello.com/c/4C8w1z5h/17-task-dif-settings-v2-priority-multiplier
PRIORITY = {'easy': 1,
            'medium': 1.5,
            'hard': 2}
AUTH_CONF = os.path.expanduser('~') + '/.config/habitica/auth.cfg'
CACHE_CONF = os.path.expanduser('~') + '/.config/habitica/cache.cfg'

SECTION_CACHE_QUEST = 'Quest'

def colorprint(name, color):
    return (color+"{}\033[00m" .format(name))

def load_auth(configfile):
    """Get authentication data from the AUTH_CONF file."""

    logging.debug('Loading habitica auth data from %s' % configfile)

    try:
        cf = open(configfile)
    except IOError:
        logging.error("Unable to find '%s'." % configfile)
        exit(1)

    config = configparser.SafeConfigParser()
    config.readfp(cf)

    cf.close()

    # Get data from config
    rv = {}
    try:
        rv = {'url': config.get('Habitica', 'url'),
              'x-api-user': config.get('Habitica', 'login'),
              'x-api-key': config.get('Habitica', 'password')}

    except configparser.NoSectionError:
        logging.error("No 'Habitica' section in '%s'" % configfile)
        exit(1)

    except configparser.NoOptionError as e:
        logging.error("Missing option in auth file '%s': %s"
                      % (configfile, e.message))
        exit(1)

    # Return auth data as a dictionnary
    return rv


def load_cache(configfile):
    logging.debug('Loading cached config data (%s)...' % configfile)

    defaults = {'quest_key': '',
                'quest_s': 'Not currently on a quest'}

    cache = configparser.SafeConfigParser(defaults)
    cache.read(configfile)

    if not cache.has_section(SECTION_CACHE_QUEST):
        cache.add_section(SECTION_CACHE_QUEST)
    return cache


def update_quest_cache(configfile, **kwargs):
    logging.debug('Updating (and caching) config data (%s)...' % configfile)

    cache = load_cache(configfile)

    for key, val in kwargs.items():
        cache.set(SECTION_CACHE_QUEST, key, val)

    with open(configfile, 'wb') as f:
        cache.write(f)

    cache.read(configfile)

    return cache


def get_task_ids(tids):
    """
    handle task-id formats such as:
        habitica todos done 3
        habitica todos done 1,2,3
        habitica todos done 2 3
        habitica todos done 1-3,4 8
    tids is a seq like (last example above) ('1-3,4' '8')
    """
    logging.debug('raw task ids: %s' % tids)
    task_ids = []
    for raw_arg in tids:
        for bit in raw_arg.split(','):
            if '-' in bit:
                start, stop = [int(e) for e in bit.split('-')]
                task_ids.extend(range(start, stop + 1))
            else:
                task_ids.append(int(bit))
    return [e - 1 for e in set(task_ids)]


def updated_task_list(tasks, tids, cid = None):
    for tid in sorted(tids, reverse=True):
        if cid != None:
            tasks[tid]['checklist'][cid]['completed'] = True
        else: del(tasks[tid])
    return tasks

def print_task_list(tasks):
    for i, task in enumerate(tasks):
        completed = 'x' if task['completed'] else ' '
        if 'date' in task and task['date'] != 'None':
            date_string = task['date'][:10]
            print('[%s] %s %s %s' % (completed, i + 1, task['text'].encode('utf8'), colorprint('| due to:'+date_string, RED)))
        else: print('[%s] %s %s' % (completed, i + 1, task['text'].encode('utf8')))
        if 'checklist' in task:
            for j, checklist in enumerate(task['checklist']):
                completed_checklist = colorprint('x', GREEN) if checklist['completed'] else ' '
                print ('  '+'[%s] %s %s' % (completed_checklist, j + 1, checklist['text'].encode('utf8')))

def qualitative_task_score_from_value(value):
    # task value/score info: http://habitica.wikia.com/wiki/Task_Value
    scores = ['*', '**', '***', '****', '*****', '******', '*******']
    breakpoints = [-20, -10, -1, 1, 5, 10]
    return scores[bisect(breakpoints, value)]

def sleep_or_not(data):
    if data: return "sleeping"
    else: return "awake"


def cli():
    """Habitica command-line interface.

    Usage: habitica [--version] [--help]
                    <command> [<args>...] [--dif=<d>] [--date=<d>] [--task=<d>]
                    [--verbose | --debug]

    Options:
      -h --help         Show this screen
      --version         Show version
      --dif=<d>         (easy | medium | hard) [default: easy]
      --date=<d>        [default: None]
      --task=<d>        [default: -1]
      --verbose         Show some logging information
      --debug           Some all logging information

    The habitica commands are:
      status                  Show HP, XP, GP, and more
      habits                  List habit tasks
      habits up <task-id>     Up (+) habit <task-id>
      habits down <task-id>   Down (-) habit <task-id>
      dailies                 List daily tasks
      dailies done            Mark daily <task-id> complete
      dailies undo            Mark daily <task-id> incomplete
      todos                   List todo tasks
      todos done <task-id>    Mark one or more todo <task-id> completed
      todos done <task-id>.<checklist-id> Mark one todo <checklist-id> in <task-id> completed
      todos add <task>        Add todo with description <task>
      todos add_cl <task-id>  Add checklist item with description <task>
      server                  Show status of Habitica service
      home                    Open tasks page in default browser
      pet                     Check pet and feed if possible
      egg                     Check egg and hatch if possible
      sleep                   Check sleeping status and moving in/leaving inn

    For `habits up|down`, `dailies done|undo`, and `todos done`, you can pass
    one or more <task-id> parameters, using either comma-separated lists or
    ranges or both. For example, `todos done 1,3,6-9,11`.
    """

    # set up args
    args = docopt(cli.__doc__, version=VERSION)

    # set up logging
    if args['--verbose']:
        logging.basicConfig(level=logging.INFO)
    if args['--debug']:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug('Command line args: {%s}' %
                  ', '.join("'%s': '%s'" % (k, v) for k, v in args.items()))

    # Set up auth
    auth = load_auth(AUTH_CONF)

    # Prepare cache
    cache = load_cache(CACHE_CONF)

    # instantiate api service
    hbt = api.Habitica(auth=auth)

    # GET server status
    if args['<command>'] == 'server':
        server = hbt.status()['data']
        if server['status'] == 'up':
            print('Habitica server is up')
        else:
            print('Habitica server down... or your computer cannot connect')

    # open HABITICA_TASKS_PAGE
    elif args['<command>'] == 'home':
        home_url = '%s%s' % (auth['url'], HABITICA_TASKS_PAGE)
        print('Opening %s' % home_url)
        open_new_tab(home_url)

    # GET user
    elif args['<command>'] == 'status':

        # gather status info
        user = hbt.user()['data']
        party = hbt.groups.party()
        stats = user.get('stats', '')
        items = user.get('items', '')
        food_count = sum(items['food'].values())
        user_status = sleep_or_not(user['preferences']['sleep'])

        # gather quest progress information (yes, janky. the API
        # doesn't make this stat particularly easy to grab...).
        # because hitting /content downloads a crapload of stuff, we
        # cache info about the current quest in cache.
        quest = 'Not currently on a quest'
        # if (party is not None and party.get('quest', '')):
        if party is not None and party['data'].get('quest') and party['data']['quest']['active']:
            quest_key = party['data']['quest']['key']
            if cache.get(SECTION_CACHE_QUEST, 'quest_key') != quest_key:
                # we're on a new quest, update quest key
                logging.info('Updating quest information...')
                content = hbt.content()
                quest_type = ''
                quest_max = '-1'
                quest_title = content['data']['quests'][quest_key]['text']

                # if there's a content/quests/<quest_key/collect,
                # then drill into .../collect/<whatever>/count and
                # .../collect/<whatever>/text and get those values
                if content['data'].get('quests', {}).get(quest_key, {}).get('collect'):
                    logging.debug("\tOn a collection type of quest")
                    quest_type = 'collect'
                    clct = content['data']['quests'][quest_key]['collect'].values()[0]
                    quest_max = clct['count']
                # else if it's a boss, then hit up
                # content/quests/<quest_key>/boss/hp
                elif content['data'].get('quests', {}).get(quest_key, {}).get('boss'):
                    logging.debug("\tOn a boss/hp type of quest")
                    quest_type = 'hp'
                    quest_max = content['data']['quests'][quest_key]['boss']['hp']

                # store repr of quest info from /content
                cache = update_quest_cache(CACHE_CONF,
                                           quest_key=str(quest_key),
                                           quest_type=str(quest_type),
                                           quest_max=str(quest_max),
                                           quest_title=str(quest_title))

            # now we use /party and quest_type to figure out our progress!
            quest_type = cache.get(SECTION_CACHE_QUEST, 'quest_type')
            if quest_type == 'collect':
                qp_tmp = party['data']['quest']['progress']['collect']
                quest_progress = qp_tmp.values()[0]
            else:
                quest_progress = party['data']['quest']['progress']['hp']

            quest = '%s/%s "%s"' % (
                    str(int(quest_progress)),
                    cache.get(SECTION_CACHE_QUEST, 'quest_max'),
                    cache.get(SECTION_CACHE_QUEST, 'quest_title'))

        # prepare and print status strings
        title = 'Level %d %s' % (stats['lvl'], stats['class'].capitalize())
        health = '%d/%d' % (stats['hp'], stats['maxHealth'])
        xp = '%d/%d' % (int(stats['exp']), stats['toNextLevel'])
        mana = '%d/%d' % (int(stats['mp']), stats['maxMP'])
        currentPet = items.get('currentPet', '')
        pet = '%s (%d food items)' % (currentPet, food_count)
        mount = items.get('currentMount', '')
        summary_items = ('health', 'xp', 'mana', 'quest', 'pet', 'mount')
        len_ljust = max(map(len, summary_items)) + 1
        print('-' * len(title))
        print(title)
        print('-' * len(title))
        print('%s %s' % ('Health:'.rjust(len_ljust, ' '), health))
        print('%s %s' % ('XP:'.rjust(len_ljust, ' '), xp))
        print('%s %s' % ('Mana:'.rjust(len_ljust, ' '), mana))
        print('%s %s' % ('Pet:'.rjust(len_ljust, ' '), pet))
        print('%s %s' % ('Mount:'.rjust(len_ljust, ' '), mount))
        print('%s %s' % ('Quest:'.rjust(len_ljust, ' '), quest))
        print('%s %s' % ('Status:'.rjust(len_ljust, ' '), user_status))

    # GET/POST habits
    elif args['<command>'] == 'habits':
        task_data = hbt.tasks.user()['data']
        habits = [task for i, task in enumerate(task_data) if task['type'] == 'habit']
        if 'up' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:])
            for tid in tids:
                tval = habits[tid]['value']

                hbt.tasks.score(_id=habits[tid]['id'],
                               _direction='up', _method='post')
                print('incremented task \'%s\''
                      % habits[tid]['text'].encode('utf8'))
                habits[tid]['value'] = tval + (TASK_VALUE_BASE ** tval)
                sleep(HABITICA_REQUEST_WAIT_TIME)
        elif 'down' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:])
            for tid in tids:
                tval = habits[tid]['value']
                hbt.tasks.score(_id=habits[tid]['id'],
                               _direction='down', _method='post')
                print('decremented task \'%s\''
                      % habits[tid]['text'].encode('utf8'))
                habits[tid]['value'] = tval - (TASK_VALUE_BASE ** tval)
                sleep(HABITICA_REQUEST_WAIT_TIME)
        for i, task in enumerate(habits):
            score = qualitative_task_score_from_value(task['value'])
            print('[%s] %s %s' % (score, i + 1, task['text'].encode('utf8')))

    # GET/PUT tasks:daily
    elif args['<command>'] == 'dailies':
        task_data = hbt.tasks.user()['data']
        dailies = [task for i, task in enumerate(task_data) if task['type'] == 'daily']
        if 'done' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:])
            for tid in tids:
                hbt.tasks.score(_id=dailies[tid]['id'],
                               _direction='up', _method='post')
                print('marked daily \'%s\' completed'
                      % dailies[tid]['text'].encode('utf8'))
                dailies[tid]['completed'] = True
                sleep(HABITICA_REQUEST_WAIT_TIME)
        elif 'undo' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:])
            for tid in tids:
                hbt.tasks.score(_id=dailies[tid]['id'],
                               _method='put', completed=False)
                print('marked daily \'%s\' incomplete'
                      % dailies[tid]['text'].encode('utf8'))
                dailies[tid]['completed'] = False
                sleep(HABITICA_REQUEST_WAIT_TIME)
        print_task_list(dailies)

    # GET tasks:todo
    elif args['<command>'] == 'todos':
        task_data = hbt.tasks.user()['data']
        todos = [task for i, task in enumerate(task_data) if task['type'] == 'todo' and not task['completed']]
        
        if 'done' in args['<args>']:
            ids = args['<args>'][1:]
            ## for checklist
            if len([x for x in ids if '.' in x]):
                cid = int(ids[0].split('.')[1]) - 1
                tids = get_task_ids(ids[0].split('.')[0])
                tid = tids[0]
                todos[tid]['checklist']
                hbt.tasks.checklist.score(_id=todos[tid]['id'],
                                _cid=todos[tid]['checklist'][cid]['id'],
                                _method='post', completed = True)
                print('marked todo \'%s\' complete'
                      % todos[tid]['text'].encode('utf8'))
                sleep(HABITICA_REQUEST_WAIT_TIME)
                todos = updated_task_list(todos, tids, cid)
            ## for task
            else:
                tids = get_task_ids(ids)
                
                for tid in tids:
                    hbt.tasks.score(_id=todos[tid]['id'],
                                   _direction='up', _method='post', completed = True)
                    print('marked todo \'%s\' complete'
                          % todos[tid]['text'].encode('utf8'))
                    sleep(HABITICA_REQUEST_WAIT_TIME)
                todos = updated_task_list(todos, tids)
        elif 'add' in args['<args>']:
            ttext = ' '.join(args['<args>'][1:])
            
            hbt.tasks.user(type='todo',
                       text=ttext,
                       priority=PRIORITY[args['--dif']],
                       date=args['--date'],
                       _method='post')
            todos.insert(0, {'completed': False, 'text': ttext})
            print('added new todo \'%s\'' % ttext.encode('utf8'))
        elif 'add_cl' in args['<args>']:
            if args['--task'] == '-1':
                raise ValueError('task id must be given after --task=')
            else:
                ttext = ' '.join(args['<args>'][1:])
                tid = get_task_ids([args['--task']])[0]
                hbt.tasks.checklist(type='todo',
                           _id=todos[tid]['id'],
                           text=ttext,
                           _method='post')
            if 'checklist' not in todos[tid]:
                todos[tid]['checklist'] = []
            todos[tid]['checklist'].insert(0, {'completed': False, 'text': ttext})
        print_task_list(todos)

    ##GET/POST pets
    elif args['<command>'] == 'pet':
        user = hbt.user()['data']
        pets = user['items']['pets']
        food = user['items']['food']
        available_food = [key for key in food if food[key] != 0]
        available_pet = [i for i,j in sorted(pets.items(), key = lambda x: x[1], reverse=True) if j !=-1 ]
        if len(available_food) and len(available_pet):
            first_pet = available_pet[0]
            feeding_responese = raw_input("Do you want to feed "+first_pet+"?[y/n] ")
            if feeding_responese == 'y':
                for item in available_food:
                    pet_response = hbt.user.feed(_inventory1 = first_pet, _inventory2 = item, _method = 'post')
                    print pet_response['message']
            else:
                print colorprint("Ok, pets need more care, so try to feed them next time", RED)
        else:
            print "Oops, no food available"

    ##GET/POST pets
    elif args['<command>'] == 'egg':
        user = hbt.user()['data']
        pets = user['items']['pets']
        eggs = user['items']['eggs']
        potions = user['items']['hatchingPotions']
        available_potions = [key for key in potions if potions[key] != 0]
        available_eggs = [key for key in eggs if eggs[key] != 0]
        possible_hatching = list(itertools.product(available_eggs, available_potions))
        available_hatching = [i for i in possible_hatching if not pets.get(i[0]+"-"+i[1])]
        if len(available_hatching):
            hatching_responese = raw_input("Do you want to hatch a "+available_hatching[0][1]+" "+available_hatching[0][0]+"? [y/n] ")
            if hatching_responese == 'y':
                hatch_response = hbt.user.hatch(_inventory1 = available_hatching[0][0], _inventory2 = available_hatching[0][1], _method = 'post')
                print hatch_response['message']
            else:
                print colorprint("Ok, you are so boring", RED)
        else:
            print "No egg can be hatched"

    ##POST sleep
    elif args['<command>'] == 'sleep':
        user_status = hbt.user()['data']['preferences']['sleep']
        if user_status:
            print "You are sleeping!"
            awake = raw_input("Do you want to leave inn now?[y/n] ")
            if awake == 'y': 
                hbt.user.sleep(_method='post')
                print "Work hard, so you can play harder!"
            else: 
                print "Ok, sleep tight!"
        else:
            sleeping = raw_input("Do you want to sleep now?[y/n] ")
            if sleeping == 'y': 
                hbt.user.sleep(_method='post')
                print "Have a nice dream :)"
            else: 
                print "Then continue your work, please!"

if __name__ == '__main__':
    cli()
