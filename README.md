# charts-transfer
scripts to download/upload forecast charts

### cron job example of running the script in igp conda environment
```bash
0 8 * * * /home/ubuntu/miniconda3/envs/igp/bin/python /home/ubuntu/IGP/code/charts-transfer/ftp-copier.py > /home/ubuntu/IGP/code/charts-transfer/error.log 2>&1
```
