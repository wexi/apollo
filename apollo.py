#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Use venus[.sh] to search for TV Shows
#
import argparse
import pathlib
import re
import subprocess
from local import SERVERS, APOLLO, TVLIVE, DIR


class Action(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '-m':
            setattr(namespace, 'media', 'movies')
            setattr(namespace, self.dest, values)
        else:
            values += '/1'
            setattr(namespace, 'media', 'tvshows/' + values.split('/')[1])
            setattr(namespace, self.dest, values.split('/')[0])


parser = argparse.ArgumentParser()
parser.add_argument('-m', dest='video', action=Action,
                    metavar='MOVIE_TITLE', help='Partial name, case ignored')
parser.add_argument('-t', dest='video', action=Action,
                    metavar='TVSHOW_NAME', help='name/#, 1=latest and default')
parser.add_argument('-p', type=int, dest='ping', default=3,
                    metavar='COUNT', help='Nearest server search fping COUNT')
parser.add_argument('-x', dest='exec', action='store_true', default=False,
                    help='Play found  playlist')
parser.add_argument('-y', dest='year', metavar='YEAR',
                    help='Movie or TV Show (YEAR)')
parser.add_argument('word', nargs='*', help='Movie title, case ignored')
parser.add_argument('--wget', action='store_true', help='Preserve wget.m3u8')
arg = parser.parse_args()

if arg.ping:
    try:
        args = ['fping', '-aeqc', "{}".format(arg.ping)]
        args.extend(SERVERS)
        fping = subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=arg.ping+3, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        exit(0)
    else:
        pings = fping.stderr.decode('utf-8').split('\n', -1)
        servers = []
        for ping in pings:
            ma = re.match(r'^(\S+).+max =[^/]+/([^/]+)/', ping)
            if ma is None:
                break
            servers.append((float(ma.group(2)), ma.group(1)))

    try:
        delay, server = min(servers)
    except ValueError:
        print('NO REACHABLE SERVER')
        exit(1)
    else:
        print('Best server:', server, 'delay (ms):', delay)
else:
    server = servers[0]

apollo = 'https://' + server + APOLLO

if arg.video is None:           # Action never called (not -m or -t)
    if arg.word:
        video = ' '.join(arg.word)
        media = 'movies'
    else:
        video = None
        media = 'livetv'
else:
    video = arg.video
    media = arg.media

if video is None:
    SEARCH = TVLIVE
    Search = re.compile('|'.join(SEARCH))
else:
    se = re.match(r'^(.*)\s+\((\d\d\d\d)\)$', video)
    if se:
        VIDEO = se.group(1)
        YEAR = se.group(2)
    else:
        VIDEO = video
        YEAR = "{:4s}".format(arg.year) if arg.year else r'\d\d\d\d'
    SEARCH = VIDEO + r'[^\(]*\(' + YEAR + r'\)' + (
        r'$' if media.startswith('m') else r'\sS\d\d\sE\d\d$')
    Search = re.compile(SEARCH, re.IGNORECASE)

dir = pathlib.Path.home().joinpath(*DIR)
dir.mkdir(exist_ok=True)
wlist = dir.joinpath('wget.m3u8')
mlist = dir.joinpath(media.rsplit('/', 1)[0] + '.m3u8')

try:
    subprocess.run(['wget', '-O', wlist, apollo + media],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=10, check=True)
except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
    exit(0)                     # ends venus loop

names = set()
with wlist.open('rt') as fi:
    with mlist.open('wt') as fo:
        line = fi.readline()
        if line.startswith('#EXTM3U'):
            fo.write(line)
            while line:
                if line.startswith('#EXTINF'):
                    ss = Search.search(line)
                    if ss:
                        name = ss.group(0)
                        if video or name not in names:
                            names.add(name)
                            fo.write(line)
                            line = fi.readline()
                            fo.write(line)
                line = fi.readline()

if names:
    if video:                   # not livetv
        for i, name in enumerate(sorted(names), 1):
            print(i, name, sep=': ')

    if arg.exec:
        try:
            subprocess.Popen(['vlc', '--fullscreen',
                              '--one-instance', '--no-playlist-enqueue',
                              '--disable-screensaver', '2',
                              mlist.as_uri()],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print('vlc', e)

else:
    mlist.unlink()              # search failed

if not arg.wget:
    wlist.unlink()

if arg.ping:                    # since venus runs with no fping
    print('TV channels' if video is None else 'Search "' + video + '"',
          len(names), sep=': #')
exit(len(names) == 0)
