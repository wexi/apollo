

# General

**apollo.py** is a Linux script that helps to select/play [Apollo Group TV](https://apollogroup.tv/)
IPTV m3u8 content for/by the [VLC media player](https://www.videolan.org/). Your apollo subscription
details and your live TV channels of interest go into local.py.

venus.sh is a shell script that helps to locate TV Series.
See Apollo Group article: [What are the M3U & EPG urls](https://help.apollogroup.tv/support/solutions/articles/48000589710-what-are-the-m3u-epg-urls-sports-vod-url-included-).


# Usage

    $ apollo -h
    usage: apollo [-h] [-m MOVIE_TITLE] [-t TVSHOW_NAME] [-p COUNT] [-x] [-y YEAR] [--wget] [word ...]
    
    positional arguments:
      word            Movie title, case ignored
    
    optional arguments:
      -h, --help      show this help message and exit
      -m MOVIE_TITLE  Partial name, case ignored
      -t TVSHOW_NAME  name/#, 1=latest and default
      -p COUNT        Nearest server search fping COUNT
      -x              Play found playlist
      -y YEAR         Movie or TV Show (YEAR)
      --wget          Preserve wget.m3u8

By default the selected m3u8 lists are written to:

    $ ls ~/Desktop/VLC/
    livetv.m3u8  movies.m3u8  tvshows.m3u8


# Examples

    $ apollo gone with the wind
    Best server: tv4.live delay (ms): 2.8
    1: Gone with the Wind (1939)
    Search "gone with the wind": #1

    $ venus humans -y 2015
    NOT FOUND: "humans/1" -y 2015
    NOT FOUND: "humans/2" -y 2015
    NOT FOUND: "humans/3" -y 2015
    NOT FOUND: "humans/4" -y 2015
    1: HUMANS (2015) S01 E01
    2: HUMANS (2015) S01 E02
    3: HUMANS (2015) S01 E03
    4: HUMANS (2015) S01 E04
    5: HUMANS (2015) S01 E05
    6: HUMANS (2015) S01 E06
    7: HUMANS (2015) S01 E07
    8: HUMANS (2015) S01 E08
    9: HUMANS (2015) S02 E01
    10: HUMANS (2015) S02 E02
    11: HUMANS (2015) S02 E03
    12: HUMANS (2015) S02 E04
    13: HUMANS (2015) S02 E05
    14: HUMANS (2015) S02 E06
    15: HUMANS (2015) S02 E07
    16: HUMANS (2015) S02 E08
    17: HUMANS (2015) S03 E01
    18: HUMANS (2015) S03 E02
    19: HUMANS (2015) S03 E03
    20: HUMANS (2015) S03 E04
    21: HUMANS (2015) S03 E05
    22: HUMANS (2015) S03 E06
    23: HUMANS (2015) S03 E07
    24: HUMANS (2015) S03 E08
    Middle click to repeat last search with 10s fping

