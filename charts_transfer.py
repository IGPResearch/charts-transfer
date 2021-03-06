# coding: utf-8
"""
Download files from IMO's website and upload to CEDA FTP project space
"""
import configparser
from datetime import datetime, timedelta
import ftplib
# from getpass import getpass
import logging
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path
try:
    from PIL import Image
    pil_ok = True
except ImportError:
    pil_ok = False


def download(url, file_name, **req_kw):
    # get request
    img_req = requests.get(url, **req_kw)
    # img_size = len(img_req.content)

    if img_req.status_code == 200:
        # open in binary mode
        with file_name.open('wb') as file:
            # write to file
            file.write(img_req.content)
        return 0
    else:
        L.error('Failed with {} ({})'.format(img_req.status_code,
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


def upload(file_name, addr, workdir, username, password):
    """ Upload file to a protected FTP server """
    with ftplib.FTP(addr) as ftp:
        ftp.login(user=username, passwd=password)
        for subdir in workdir.split('/'):
            if ftp_directory_exists(ftp, subdir):
                ftp.cwd(subdir)
            else:
                ftp.mkd(subdir)
                ftp.cwd(subdir)
        ftp.storbinary("STOR " + file_name.name, file_name.open('rb'))
        # L.info(ftp.retrlines('LIST'))
#
#
# def delete_from_ftp(file_name, top_addr, topdir, dt, username, password):
#     workdir = '{topdir}/{dt:%Y%m%d}/IMO'.format(topdir=topdir, dt=dt)
#     with ftplib.FTP(top_addr) as ftp:
#         ftp.login(user=username, passwd=password)
#         ftp.cwd(workdir)
#         ftp.delete(file_name)


def _parse_str_seq(x):
    return [*filter(None, [i.strip() for i in x.split(',')])]


def process_chart(chart, fcst_init, fcst_hour):
    variable = chart['name'].strip()
    src, model = chart['model'].split(':')
    sub = chart.get('substitute', '').strip()

    src_user = config[src].get('username')
    src_pass = config[src].get('password')
    if src_user and src_pass:
        req_kw = dict(auth=HTTPBasicAuth(src_user, src_pass))
    else:
        req_kw = dict()

    fcst_valid = fcst_init + timedelta(hours=fcst_hour)
    url_mask = chart.get('url_mask', config[src]['url_mask'])
    url = url_mask.format(fcst_init=fcst_init,
                          fcst_valid=fcst_valid,
                          fcst_hour=fcst_hour,
                          model=model,
                          variable=variable)
    L.info('Downloading {}'.format(url))

    file_name = Path(url).name
    local_dir = (cwd / LOC_DIR / src.upper()
                 / fcst_init.strftime('%Y%m%d%H%M'))
    L.debug('local_dir={}'.format(local_dir))
    if not local_dir.exists():
        local_dir.mkdir(parents=True)
    file_name = local_dir / file_name

    err = download(url, file_name, **req_kw)
    if err != 0:
        if sub:
            L.info('Trying to substitute with {}'.format(sub))
            process_chart(config[sub], fcst_init, fcst_hour)
    else:
        # Compress images using PIL
        to_quality = config[src].get('to_quality')
        if to_quality is not None:
            if not pil_ok:
                L.warning(('PIL ImportError, '
                           'no compression applied'))
                to_quality = None
            else:
                to_quality = int(to_quality)
        # set_trace()

        if to_quality is not None:
            im = Image.open(file_name)
            new_dir = file_name.parent / 'lowres'
            if not new_dir.exists():
                new_dir.mkdir()
            file_name = new_dir / file_name.with_suffix('.jpg').name
            try:
                im.save(file_name, quality=to_quality, optimize=True)
            except OSError:
                im.convert('RGB').save(file_name,
                                       quality=to_quality, optimize=True)
            L.info('Low-res image saved to {}'.format(file_name))
        workdir = target_dir.format(fcst_day=fcst_init,
                                    source=src.upper())
        upload(file_name, ADDR, workdir, USER, PASS)


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
    config.read(cwd / 'settings.ini')

    LOC_DIR = cwd / config['general']['local_dir']

    # Set up logger parameters
    log_dir = cwd / Path(config['general']['log_dir'])
    if not log_dir.exists():
        log_dir.mkdir()
    log_file = log_dir / (config['general']['log_file']
                          .format(datetime=today.strftime('%Y%m%d%H%M')))
    # create logger
    L = logging.getLogger('charts_transfer')
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
    target_dir = config['ceda']['target_dir']

    # What charts to transfer
    chart_numbers = _parse_str_seq(config['general']['charts'])
    default_hours = config['general']['default_hours']

    for cn in chart_numbers:
        chart = config[cn]
        try:
            fcst_hours = list(eval(chart.get('fcst_hours', default_hours)))
        except TypeError:
            fcst_hours = [eval(chart.get('fcst_hours', default_hours))]
        freq = int(chart.get('freq', 1))  # 1 means every day
        if today.day % freq != 0:
            # Today is not the day for downloading this chart
            continue

        for fcst_hour in fcst_hours:
            process_chart(chart, fcst_init, fcst_hour)
