#!/bin/bash
# tvshow search example: venus humans -y 2015

COUNTER=1
until apollo -p 0 -t "${1}/${COUNTER}" ${2} ${3}; do
    echo NOT FOUND: \"${1}/${COUNTER}\" ${2} ${3}
    (( COUNTER++ ))
done
echo Middle click to repeat last search with 10s fping
echo apollo -p 10 -t \"${1}/${COUNTER}\" ${2} ${3} | xclip
