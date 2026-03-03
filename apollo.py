#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Use venus[.sh] to search for TV Shows
#
import argparse
import pathlib
import re
import subprocess
import sys
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
parser.add_argument('--debug', action='store_true',
                    help='Print network/debug details to stderr')
arg = parser.parse_args()

if arg.ping:
    args = ['fping', '-aeqc', "{}".format(arg.ping)]
    args.extend(SERVERS)
    try:
        fping = subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=arg.ping+3, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        if arg.debug:
            print('fping failed:', e, file=sys.stderr)
        fping = None

    servers = []
    if fping is not None:
        pings = fping.stderr.decode('utf-8', errors='replace').splitlines()
        for ping in pings:
            ma = re.match(r'^(\S+)\s*:.*min/avg/max = [^/]+/([^/]+)/', ping)
            if ma is None:
                continue
            servers.append((float(ma.group(2)), ma.group(1)))

    if servers:
        delay, server = min(servers)
        print('Best server:', server, 'delay (ms):', delay)
    else:
        server = SERVERS[0]
        if arg.debug:
            print('No fping-selected server; using default:', server,
                  file=sys.stderr)
else:
    server = SERVERS[0]

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

outdir = pathlib.Path.home().joinpath(*DIR)
outdir.mkdir(exist_ok=True)
wlist = outdir.joinpath('wget.m3u8')
mlist = outdir.joinpath(media.rsplit('/', 1)[0] + '.m3u8')

servers = [server] + [s for s in SERVERS if s != server]
for server in servers:
    apollo = 'https://' + server + APOLLO
    try:
        wget = subprocess.run(['wget', '-O', wlist, apollo + media],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              timeout=10, check=True)
    except FileNotFoundError:
        print('wget command not found', file=sys.stderr)
        exit(2)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        if arg.debug:
            stderr = (e.stderr.decode('utf-8', errors='replace').strip()
                      if hasattr(e, 'stderr') and e.stderr else str(e))
            if stderr:
                print('wget failed on', server, ':',
                      stderr.rsplit('\n', 1)[-1], file=sys.stderr)
        continue
    else:
        if arg.debug and server != servers[0]:
            print('Using fallback server:', server, file=sys.stderr)
        break
else:
    print('Unable to fetch playlist from configured servers', file=sys.stderr)
    exit(2)

names = set()
with wlist.open('rt') as fi:
    with mlist.open('wt') as fo:
        line = fi.readline()
        if line.lstrip().startswith('#EXTM3U'):
            fo.write(line)
            while line:
                if line.lstrip().startswith('#EXTINF'):
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
        except OSError as e:
            print('vlc', e)

else:
    mlist.unlink()              # search failed

if not arg.wget:
    wlist.unlink()

if arg.ping:                    # since venus runs with no fping
    print('TV channels' if video is None else 'Search "' + video + '"',
          len(names), sep=': #')
exit(len(names) == 0)
