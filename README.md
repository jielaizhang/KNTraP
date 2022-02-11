# KNTrap

---
### Create JSON

Create JSON files for DECam given an observing sequence table

positional arguments: <br>
  filename              Sequence file name (CSV)<br>
<br>
optional arguments:<br>
  -h, --help            show this help message and exit<br>
  -oh OVERHEAD, --overhead OVERHEAD<br>
                        Overhead between exposures (s)<br>
  -max MAX_TIME, --max-time MAX_TIME<br>
                        Maximim time per sequence (hr)<br>
  -pi PI, --principal-investigator PI<br>
                        Program Principal Investigator<br>
  -prog PROGRAM, --program PROGRAM<br>
                        Program name<br>
  -id PROPID, --proposal-id PROPID<br>
                        Proposal ID<br>
  -d OUTDIR, --directory OUTDIR<br>
                        Path to the directory where the JSON files will be
                        written<br>

Example:
```
python create_json.py observing_sequence.csv -max 2 -pi "Albert Einstein" -prog "Fun With Relativity" -id NOAO-1908A --directory JSON_files
```
