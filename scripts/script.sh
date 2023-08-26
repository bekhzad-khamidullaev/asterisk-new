#asterisk -rx 'queue show queue_01'| grep dynamic |grep Unavailable | grep "no calls yet" | awk {'print $1'} | while read line ; do  asterisk -rx "queue remove member $line from queue_01"; done
asterisk -rx 'queue show queue_01'| grep dynamic |grep pause |grep Unavailable| awk {' print $1" "$7'}| while read agent time ; do if [ $time -gt 1200 ] ; then asterisk -rx "queue remove member $agent from queue_01";else echo "no agents to remove"; fi;done

