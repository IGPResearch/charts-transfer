# coding: utf-8
"""
Download files from IMO's website and upload to CEDA FTP project space
"""
import configparser
from datetime import datetime
import ftplib
# from getpass import getpass
import logging
from pathlib import Path


def ftp_directory_exists(ftp, d):
    """Check if directory exists (in current location)"""
    filelist = []
    ftp.retrlines('LIST', filelist.append)
    for f in filelist:
        if f.split()[-1] == d and f.upper().startswith('D'):
            return True
    return False


def ftp_copy(addr, username, password, src_dir, tgt_dir, fnames):
    """Copy files across directories on a protected FTP server"""
    temp_binary = Path('/tmp/temp_binary_stream.bin')
    with ftplib.FTP(addr) as ftp:
        ftp.login(user=username, passwd=password)
        for subdir in tgt_dir.split('/'):
            if ftp_directory_exists(ftp, subdir):
                ftp.cwd(subdir)
            else:
                ftp.mkd(subdir)
                ftp.cwd(subdir)
        ftp.cwd('/')
        filelist = []
        ftp.retrlines('LIST ' + src_dir, filelist.append)
        filelist = [f.split()[-1] for f in filelist]
        for f in filelist:
            if f in fnames:
                L.info('Copying {}'.format(f))
                # Change directory to src_dir
                ftp.cwd(src_dir)
                with temp_binary.open('wb') as io:
                    ftp.retrbinary("RETR " + f, io.write)
                # Change to target dir and upload the file there
                ftp.cwd('/')
                ftp.cwd(tgt_dir)
                with temp_binary.open('rb') as io:
                    ftp.storbinary("STOR " + f, io)
                ftp.cwd('/')


if __name__ == '__main__':
    cwd = Path(__file__).parent.absolute()
    today = datetime.utcnow()
    # Temporary workaround
    if today.hour >= 21:
        fcst_init = today.replace(hour=12, minute=0, second=0, microsecond=0)
    else:
        fcst_init = today.replace(hour=0, minute=0, second=0, microsecond=0)

    # Initialise config parser
    config = configparser.ConfigParser()
    # Read configs from the same directory
    config.read(cwd / 'ftp-copy-settings.ini')

    # Set up logger parameters
    log_dir = cwd / Path(config['general']['log_dir'])
    if not log_dir.exists():
        log_dir.mkdir()
    log_file = log_dir / (config['general']['log_file']
                          .format(datetime=today.strftime('%Y%m%d%H%M')))
    # create logger
    L = logging.getLogger('ftp-copier')
    L.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    # create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    fh.setFormatter(formatter)
    # add the handlers to the logger
    L.addHandler(fh)

    # CEDA configs
    ADDR = config['ceda']['address']
    USER = config['ceda']['username']
    PASS = config['ceda']['password']  # , getpass('password:'))

    # Directories
    src_dir = config['dirs']['source'].format(fcst_day=fcst_init)
    tgt_dir = config['dirs']['target'].format(fcst_day=fcst_init)

    # What charts to transfer
    file_mask = config['dirs']['file_mask']
    default_hours = config['general']['default_hours']
    fcst_hours = list(eval(default_hours))
    fnames = []
    for fcst_hour in fcst_hours:
        fnames.append(file_mask.format(fcst_day=fcst_init,
                                       fcst_hour=fcst_hour))
    ftp_copy(ADDR, USER, PASS, src_dir, tgt_dir, fnames)
