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
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from local import SERVERS, APOLLO, TVLIVE, DIR


DOWNLOAD_SUBDIR = 'downloads'


class Action(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '-m':
            setattr(namespace, 'media', 'movies')
            setattr(namespace, self.dest, values)
        else:
            values += '/1'
            setattr(namespace, 'media', 'tvshows/' + values.split('/')[1])
            setattr(namespace, self.dest, values.split('/')[0])


def sanitize_filename(name):
    sanitized = re.sub(r'[^\w .()\-]+', '_', name).strip()
    return sanitized.rstrip('.') or 'apollo_download'


def parse_m3u_attributes(line):
    attrs = {}
    for key, value in re.findall(r'([A-Z0-9\-]+)=((?:"[^"]*")|[^,]+)', line):
        attrs[key] = value.strip('"')
    return attrs


def download_subtitle_track(uri, target, debug=False):
    if target.exists():
        return target
    alt = target.with_suffix('.srt')
    if alt.exists():
        return alt

    args = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'warning',
        '-n', '-i', uri, '-map', '0', '-c', 'copy', str(target)
    ]
    try:
        subprocess.run(args, check=True)
        return target
    except FileNotFoundError:
        print('ffmpeg command not found', file=sys.stderr)
        return None
    except subprocess.CalledProcessError as err:
        if debug:
            print('Subtitle copy failed with exit code', err.returncode,
                  'for', uri, file=sys.stderr)

    # Fallback: convert to plain srt when copy mode is unsupported.
    args = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'warning',
        '-n', '-i', uri, '-c:s', 'srt', str(alt)
    ]
    try:
        subprocess.run(args, check=True)
        return alt
    except FileNotFoundError:
        print('ffmpeg command not found', file=sys.stderr)
        return None
    except subprocess.CalledProcessError as err:
        if debug:
            print('Subtitle conversion failed with exit code', err.returncode,
                  'for', uri, file=sys.stderr)
        return None


def download_subtitles(base, subtitles, dl_dir, debug=False):
    subfile = dl_dir.joinpath(base + '.subtitles.txt')
    downloaded = 0

    with subfile.open('wt') as fo:
        for i, sub in enumerate(subtitles, 1):
            label = sub['name'] or 'unnamed'
            lang = sub['language'] or 'unknown'
            slug = sanitize_filename('_'.join(
                p for p in (sub['language'], sub['name']) if p))
            if not slug:
                slug = f'track_{i:02d}'
            slug = slug.replace(' ', '_').lower()
            target = dl_dir.joinpath(f"{base}.subtitle.{i:02d}.{slug}.vtt")

            fetched = download_subtitle_track(sub['uri'], target, debug=debug)
            if fetched is None:
                fo.write(f"{i}. {label} [{lang}] {sub['uri']} -> FAILED\n")
            else:
                fo.write(f"{i}. {label} [{lang}] {sub['uri']} -> {fetched}\n")
                downloaded += 1

    print('Subtitles:', len(subtitles), 'track(s) discovered,', downloaded,
          'saved, details in', subfile)
    return downloaded


def discover_subtitles(stream_url, debug=False):
    req = Request(stream_url, headers={'User-Agent': 'apollo.py'})
    try:
        with urlopen(req, timeout=10) as response:
            # Stream endpoints may be long-running; only sample the prefix.
            blob = response.read(262144)
    except Exception as err:  # network/parsing issues should not break download
        if debug:
            print('Subtitle discovery failed:', err, file=sys.stderr)
        return []

    text = blob.decode('utf-8', errors='replace')
    if '#EXT' not in text:
        return []

    subtitles = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#EXT-X-MEDIA') and 'TYPE=SUBTITLES' in line:
            attrs = parse_m3u_attributes(line)
            uri = attrs.get('URI')
            if uri:
                subtitles.append({
                    'language': attrs.get('LANGUAGE', ''),
                    'name': attrs.get('NAME', ''),
                    'uri': urljoin(stream_url, uri),
                })
    return subtitles


def download_stream(name, stream_url, outdir, debug=False):
    dl_dir = outdir.joinpath(DOWNLOAD_SUBDIR)
    dl_dir.mkdir(exist_ok=True)

    base = sanitize_filename(name)
    target = dl_dir.joinpath(base + '.mkv')

    subtitles = discover_subtitles(stream_url, debug=debug)

    args = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'warning', '-stats',
        '-n', '-i', stream_url,
        '-map', '0', '-c', 'copy', str(target)
    ]
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError:
        print('ffmpeg command not found', file=sys.stderr)
        return False
    except subprocess.CalledProcessError as err:
        print('ffmpeg download failed with exit code', err.returncode,
              file=sys.stderr)
        return False

    print('Downloaded:', target)
    if subtitles:
        download_subtitles(base, subtitles, dl_dir, debug=debug)
    else:
        print('Subtitles: none discovered in the stream manifest')
    return True


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
parser.add_argument('--download', action='store_true',
                    help='Download only if exactly one matched stream is found;'
                    ' also saves subtitle tracks when available')
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
        subprocess.run(['wget', '-O', wlist, apollo + media],
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
matches = []
with wlist.open('rt') as fi:
    with mlist.open('wt') as fo:
        line = fi.readline()
        if line.lstrip().startswith('#EXTM3U'):
            fo.write(line)
            while line:
                if line.lstrip().startswith('#EXTINF'):
                    info_line = line
                    url_line = fi.readline()
                    if not url_line:
                        break

                    ss = Search.search(info_line)
                    if ss:
                        name = ss.group(0)
                        if video or name not in names:
                            names.add(name)
                            fo.write(info_line)
                            fo.write(url_line)
                            matches.append((name, url_line.strip()))
                    line = fi.readline()
                else:
                    line = fi.readline()

exit_code = 0
if names:
    if video:                   # not livetv
        for i, name in enumerate(sorted(names), 1):
            print(i, name, sep=': ')

    if arg.download:
        if len(matches) != 1:
            print('Ambiguous: found', len(matches),
                  'matching streams. Refine your search to one result.')
            exit_code = 1
        else:
            ok = download_stream(matches[0][0], matches[0][1], outdir,
                                 debug=arg.debug)
            if not ok:
                exit_code = 2

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
    exit_code = 1

if not arg.wget:
    wlist.unlink()

if arg.ping:                    # since venus runs with no fping
    print('TV channels' if video is None else 'Search "' + video + '"',
          len(names), sep=': #')
exit(exit_code)
