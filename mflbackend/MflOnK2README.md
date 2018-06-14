Before restarting the backend, run the command
`python makedump.py`
This will extract the current state of the paradigms (from ES) and write it to
a tmp file.

After this, you can restart mflbackend, by running:
`supervisorctl -c /etc/supervisord.d/fkkarp.conf restart morfologilabbet`

This will read the tmp file and start morfologilabbet from this state.

If you forget to run the dump command, the restarted backend will use old data
when calculating the inflections. The tmp file is updated every night by a cron
job, to minimize the risk of old data getting used if the backend is restarted
without the `makedum.py`.

