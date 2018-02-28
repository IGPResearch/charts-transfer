# charts-transfer
scripts to download/upload forecast charts

### create Python environment using miniconda
```bash
conda env create -f environment.yml
```

### cron job example of running the script in igp conda environment
```bash
0 9 * * * /home/ubuntu/miniconda3/envs/igp/bin/python /home/ubuntu/IGP/code/charts-transfer/charts_transfer.py > /home/ubuntu/IGP/code/charts-transfer/error.log 2>&1
```
