#!/bin/sh

# Recording file script. v0.5
# Arg1 - In/Out removed
# Arg1 - Directory Arg2 - who calles, Arg3 - Answered, Arg4 - Time, Arg5 - Date
# Arg1 - Directory, Arg2 - Date, Arg3 - Time, Arg4 - First number, Arg5 - Second number
# Arg1 - Directory, Arg2 - Date, Arg3 - Time, Arg4 - First number, Arg5 - Second number, Arg6 - Time Attribute
# Arg1 - Directory, Arg2 - Date, Arg3 - Time, Arg4 - First number, Arg5 - Second number, Arg6 - FileName, Arg7 - Time Attribute

MAINDIR="$1"
DATESTAMP="$2"
TIMESTAMP="$3"
FIRSTN="$4"
SECONDN="$5"
FILENAME="$6"
TIMEATTR="$7"

mkdir -p $MAINDIR
mkdir -p $MAINDIR/$DATESTAMP
case $TIMEATTR in
'D')
mkdir -p $MAINDIR/$DATESTAMP/$SECONDN
mkdir -p $MAINDIR/$DATESTAMP/$SECONDN/DayTime
lame /var/spool/asterisk/monitor/$FILENAME.wav $MAINDIR/$DATESTAMP/$SECONDN/DayTime/$TIMESTAMP--$FIRSTN.mp3
chmod 777 $TIMESTAMP--$FIRSTN.mp3
;;
*)
mkdir -p $MAINDIR/$DATESTAMP/$SECONDN
lame /var/spool/asterisk/monitor/$FILENAME.wav $MAINDIR/$DATESTAMP/$SECONDN/$TIMESTAMP--$FIRSTN.mp3
chmod 777 $TIMESTAMP--$FIRSTN.mp3
;;
esac

