# coding: utf-8
"""
Download files from IMO's website and upload to CEDA FTP project space
"""
import configparser
from datetime import datetime
import requests
import ftplib
from pathlib import Path
# from getpass import getpass
import logging


def download(url, file_name, **req_kw):
    # get request
    img_req = requests.get(url, **req_kw)
    # img_size = len(img_req.content)

    if img_req.status_code == 200:
        # open in binary mode
        with Path(file_name).open('wb') as file:
            # write to file
            file.write(img_req.content)
        return 0
    else:
        logger.error('Failed with {} ({})'.format(img_req.status_code,
                                                  img_req.reason))
        return 1


def ftp_directory_exists(ftp, d):
    """Check if directory exists (in current location)"""
    filelist = []
    ftp.retrlines('LIST', filelist.append)
    for f in filelist:
        if f.split()[-1] == d and f.upper().startswith('D'):
            return True
    return False


def upload(file_name, addr, topdir, dt, username, password):
    """ Upload file to a protected FTP server """
    workdir = '{topdir}/{dt:%Y%m%d}/IMO'.format(topdir=topdir, dt=dt)
    with ftplib.FTP(addr) as ftp:
        ftp.login(user=username, passwd=password)
        for subdir in workdir.split('/'):
            if ftp_directory_exists(ftp, subdir):
                ftp.cwd(subdir)
            else:
                ftp.mkd(subdir)
                ftp.cwd(subdir)
        ftp.storbinary("STOR " + Path(file_name).name, open(file_name, 'rb'))
        # logger.info(ftp.retrlines('LIST'))


def delete_from_ftp(file_name, top_addr, topdir, dt, username, password):
    workdir = '{topdir}/{dt:%Y%m%d}/IMO'.format(topdir=topdir, dt=dt)
    with ftplib.FTP(top_addr) as ftp:
        ftp.login(user=username, passwd=password)
        ftp.cwd(workdir)
        ftp.delete(file_name)


if __name__ == '__main__':
    today = datetime.utcnow()
    # Initialise config parser
    config = configparser.ConfigParser()
    # Read configs from the same directory
    config.read('settings.ini')

    LOC_DIR = Path(config['other']['local_dir'])

    # Set up logger parameters
    log_dir = Path(config['other']['log_dir'])
    if not log_dir.exists():
        log_dir.mkdir()
    log_file = log_dir / (config['other']['log_file']
                          .format(datetime=today.strftime('%Y%m%d%H%M')))
    # create logger
    logger = logging.getLogger('ftp-copier-main')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    # create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    fh.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)

    # CEDA configs
    ADDR = config['ceda']['address']
    USER = config['ceda']['username']
    PASS = config['ceda'].get('password')  # , getpass('password:'))

    topdir = config['ceda']['topdir']

    # IMO address
    TOP_URL = config['imo']['url']
    URL_MASK = ('{top_url}/{model}/{dt:%Y/%m/%d/%H}/'
                '{model}_{vrbls}_{dt:%Y%m%d%H}_{fcst:03d}.jpg')

    # Temporary workaround
    if today.hour >= 21:
        upload_time = today.replace(hour=12)
    else:
        upload_time = today.replace(hour=0)

    # Loop over forecast products and times until max_fcst
    for model in config['models']:
        vrbls = config[model]['variable']
        fcst_range = eval(config[model]['fcst_hours'])
        for fcst in fcst_range:
            url = URL_MASK.format(top_url=TOP_URL,
                                  model=model,
                                  vrbls=vrbls,
                                  dt=upload_time,
                                  fcst=fcst)
            logger.info('Downloading {}'.format(url))

            file_name = Path(url).name
            local_dir = LOC_DIR / today.strftime('%Y%m%d%H%M')
            if not local_dir.exists():
                local_dir.mkdir(parents=True)
            file_name = str(local_dir / file_name)

            err = download(url, file_name)
            if err == 0:
                upload(file_name, ADDR, topdir, today, USER, PASS)
