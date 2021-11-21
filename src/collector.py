#!/usr/bin/python3
# TODO: think about what to do about string results in future - enum? ignore?

import bs4
import click
import itertools
import logging
import requests
import time

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, REGISTRY
from prometheus_client import start_http_server

DEFAULT_PORT = 7007
LOG = logging.getLogger(__name__)

class Downstream:
    def __init__(self):
        self.index = 0  # Index
        self.lock = ""  # Lock Status, String
        self.freq = 0.0  # Frequency, MHz
        self.snr = 0.0  # SNR, dB
        self.power = 0.0  # Power Level, dBmV
        self.mod = ""  # Modulation, String

    def set_index(self, value):
        # "32"
        self.index = int(value)

    def set_lock(self, value):
        # "Locked"
        self.lock = value

    def set_freq(self, value):
        # "579 MHz"
        self.freq = float(value.split()[0])

    def set_snr(self, value):
        # "41.0 dB"
        self.snr = float(value.split()[0])

    def set_power(self, value):
        # "4.2 dBmV"
        self.power = float(value.split()[0])

    def set_mod(self, value):
        # "256 QAM"
        self.mod = value

    def __str__(self):
        return f'[{self.index}]\tStatus: {self.lock}, Freq: {self.freq}, SNR: {self.snr}, Power: {self.power}, Mod: {self.mod}'

    def __repr__(self):
        return f'[{self.index}]\tStatus: {self.lock}, Freq: {self.freq}, SNR: {self.snr}, Power: {self.power}, Mod: {self.mod}'

class Upstream:
    def __init__(self):
        self.index = 0  # Index
        self.lock = ""  # Lock Status, String
        self.freq = 0.0  # Frequency, Mhz
        self.symbol = None  # Symbol Rate
        self.power = 0.0  # Power Level, dBmV
        self.mod = ""  # Modulation, String
        self.c_type = None  # Channel Type, String

    def set_index(self, value):
        # "1"
        self.index = int(value)

    def set_lock(self, value):
        # "Locked"
        self.lock = value

    def set_freq(self, value):
        # "16  MHz"
        self.freq = float(value.split()[0])

    def set_symbol(self, value):
        # "5120"
        self.symbol = int(value)

    def set_power(self, value):
        # "36.5 dBmV"
        self.power = float(value.split()[0])

    def set_mod(self, value):
        # "QAM"
        self.mod = value

    def set_c_type(self, value):
        # "ATDMA"
        self.c_type = value

    def __str__(self):
        return f'[{self.index}]\tStatus: {self.lock}, Freq: {self.freq}, Symbol: {self.symbol}, Power: {self.power}, Mod: {self.mod}, Type: {self.c_type}'

    def __repr__(self):
        return f'[{self.index}]\tStatus: {self.lock}, Freq: {self.freq}, Symbol: {self.symbol}, Power: {self.power}, Mod: {self.mod}, Type: {self.c_type}'


class CMErrors:
    def __init__(self):
        self.index = 0  # Index
        self.unerrored = 0  # Unerrored Codewords
        self.correctable = 0  # Correctable Codewords
        self.uncorrectable = 0  # Uncorrectable Codewords

    def set_index(self, value):
        # "32"
        self.index = int(value)

    def set_unerrored(self, value):
        # "2025277531"
        self.unerrored = int(value)

    def set_correctable(self, value):
        # "284570937"
        self.correctable = int(value)

    def set_uncorrectable(self, value):
        # "0"
        self.uncorrectable = int(value)

    def __str__(self):
        return f'[{self.index}]\tUnerrored: {self.unerrored}, Correctable: {self.correctable}, Uncorrectable: {self.uncorrectable}'

    def __repr__(self):
        return f'[{self.index}]\tUnerrored: {self.unerrored}, Correctable: {self.correctable}, Uncorrectable: {self.uncorrectable}'


class XB7:
    LOGIN_URL = ''
    STATS_URL = ''

    def __init__(self, ip_address, username, password):
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.session = None

    def _do_connect(self):
        if self.session and len(self.session.cookies):
            LOG.debug('Already found session with cookie.')
            return
        LOG.debug(f'Attempting to auth with {self.ip_address} for user {self.username}')
        s = requests.Session()
        s.headers.update({'referer': f'http://{self.ip_address}/'})
        r = s.post(
            f'http://{self.ip_address}/check.jst',
            data={'username': self.username, 'password': self.password}
        )
        if len(r.cookies) == 0:
            LOG.error('Did not get login cookie, bad password?')
            return
        LOG.debug('Received login cookie.')
        self.session = s

    def _parse_downstream(self, t):
        header = t.find('thead').find('td',{'class':'acs-th'}).find('div').contents[0]
        if header != 'Downstream':
            LOG.error('Error finding downstream header.')
            return
        LOG.debug('Found downstream table.')

        # Find how many downstream channels we have
        total_channels = len(t.tbody.find_all('th')[0].find_all('td'))
        LOG.debug(f'Found {total_channels} downstream channels.')

        # Create empty downstream objects
        downstreams = [Downstream() for i in range(total_channels)]

        # t.tbody.find_all('th')[0] = Index
        for idx, c in enumerate(t.tbody.find_all('th')[0].find_all('td')):
            c_idx = c.find('div').contents[0]
            downstreams[idx].set_index(c_idx)

        # t.tbody.find_all('th')[1] = Lock Status
        for idx, c in enumerate(t.tbody.find_all('th')[1].find_all('td')):
            c_lock = c.find('div').contents[0]
            downstreams[idx].set_lock(c_lock)

        # t.tbody.find_all('th')[2] = Frequency
        for idx, c in enumerate(t.tbody.find_all('th')[2].find_all('td')):
            c_freq = c.find('div').contents[0]
            downstreams[idx].set_freq(c_freq)

        # t.tbody.find_all('th')[3] = SNR
        for idx, c in enumerate(t.tbody.find_all('th')[3].find_all('td')):
            c_snr = c.find('div').contents[0]
            downstreams[idx].set_snr(c_snr)

        # t.tbody.find_all('th')[4] = Power Level
        for idx, c in enumerate(t.tbody.find_all('th')[4].find_all('td')):
            c_power = c.find('div').contents[0]
            downstreams[idx].set_power(c_power)

        # t.tbody.find_all('th')[5] = Modulation
        for idx, c in enumerate(t.tbody.find_all('th')[5].find_all('td')):
            c_mod = c.find('div').contents[0]
            downstreams[idx].set_mod(c_mod)

        return downstreams


    def _parse_upstream(self, t):
        header = t.find('thead').find('td',{'class':'acs-th'}).find('div').contents[0]
        if header != 'Upstream':
            LOG.error('Error finding upstream header.')
            return
        LOG.debug('Found upstream table.')

        # Find how many upstream channels we have
        total_channels = len(t.tbody.find_all('th')[0].find_all('td'))
        LOG.debug(f'Found {total_channels} upstream channels.')

        # Create empty upstreams objects
        upstreams = [Upstream() for i in range(total_channels)]

        # t.tbody.find_all('th')[0] = Index
        for idx, c in enumerate(t.tbody.find_all('th')[0].find_all('td')):
            c_idx = c.find('div').contents[0]
            upstreams[idx].set_index(c_idx)

        # t.tbody.find_all('th')[1] = Lock Status
        for idx, c in enumerate(t.tbody.find_all('th')[1].find_all('td')):
            c_lock = c.find('div').contents[0]
            upstreams[idx].set_lock(c_lock)

        # t.tbody.find_all('th')[2] = Frequency
        for idx, c in enumerate(t.tbody.find_all('th')[2].find_all('td')):
            c_freq = c.find('div').contents[0]
            upstreams[idx].set_freq(c_freq)

        # t.tbody.find_all('th')[3] = Symbol Rate
        for idx, c in enumerate(t.tbody.find_all('th')[3].find_all('td')):
            c_symbol = c.find('div').contents[0]
            upstreams[idx].set_symbol(c_symbol)

        # t.tbody.find_all('th')[4] = Power Level
        for idx, c in enumerate(t.tbody.find_all('th')[4].find_all('td')):
            c_power = c.find('div').contents[0]
            upstreams[idx].set_power(c_power)

        # t.tbody.find_all('th')[5] = Modulation
        for idx, c in enumerate(t.tbody.find_all('th')[5].find_all('td')):
            c_mod = c.find('div').contents[0]
            upstreams[idx].set_mod(c_mod)

        # t.tbody.find_all('th')[6] = Channel Type
        for idx, c in enumerate(t.tbody.find_all('th')[6].find_all('td')):
            c_type = c.find('div').contents[0]
            upstreams[idx].set_c_type(c_type)

        return upstreams



    def _parse_cm_errors(self, t):
        header = t.find('thead').find('td',{'class':'acs-th'}).contents[0]
        if header != 'CM Error Codewords':
            LOG.error('Error finding cm errors header.')
            return
        LOG.debug('Found cm errors table.')

        # Find how many cm error channels we have
        total_channels = len(t.tbody.find_all('th')[0].find_all('td'))
        LOG.debug(f'Found {total_channels} cm error channels.')

        # Create empty cm error objects
        cm_errors = [CMErrors() for i in range(total_channels)]

        # t.tbody.find_all('th')[0] = Index
        for idx, c in enumerate(t.tbody.find_all('th')[0].find_all('td')):
            c_idx = c.find('div').contents[0]
            cm_errors[idx].set_index(c_idx)

        # t.tbody.find_all('th')[1] = Unerrored Codewords
        for idx, c in enumerate(t.tbody.find_all('th')[1].find_all('td')):
            c_unerrored = c.find('div').contents[0]
            cm_errors[idx].set_unerrored(c_unerrored)

        # t.tbody.find_all('th')[2] = Correctable Codewords
        for idx, c in enumerate(t.tbody.find_all('th')[2].find_all('td')):
            c_correctable = c.find('div').contents[0]
            cm_errors[idx].set_correctable(c_correctable)

        # t.tbody.find_all('th')[3] = Uncorrectable Codewords
        for idx, c in enumerate(t.tbody.find_all('th')[3].find_all('td')):
            c_uncorrectable = c.find('div').contents[0]
            cm_errors[idx].set_uncorrectable(c_uncorrectable)

        return cm_errors


    def get_html_stats(self):
        """Tested on Comcast XB7 modem with
                HW Version:2.0
                Vendor:Technicolor
                BOOT Version:S1TC-3.63.20.104
                Core Version:1.0
                Model:CGM4331COM
                Product Type:XB7
                Flash Part:8192 MB
                Download Version:Prod_20.2_d31 & Prod_20.2
        """
        self._do_connect()
        r = self.session.get(f'http://{self.ip_address}/network_setup.jst')
        LOG.debug('Retrieved stats from modem.')

        # Close session, we are done.
        if self.session:
            self.session.close()
        self.session = None

        # Parse response into data.
        soup = bs4.BeautifulSoup(r.content, 'html.parser')

        # Three tables with dynamic data I care about have data class
        # all_tables[0] = Downstream
        # all_tables[1] = Upstream
        # all_tables[2] = CM Error Codewords
        all_tables = soup.find_all('table',{'class':'data'})
    
        downstream = self._parse_downstream(all_tables[0])
        upstream = self._parse_upstream(all_tables[1])
        cm_errors = self._parse_cm_errors(all_tables[2])
        LOG.debug(f'Raw Stats Collected: Downstreams {len(downstream)}, Upstreams {len(upstream)}, CM Errors {len(cm_errors)}')

        return (downstream, upstream, cm_errors)


class XB7Collector:
    LABELS = ['ip_address', 'index']
    KEY_PREFIX = 'xb7_collector'

    def __init__(self, modem):
        '''Expecting XB7 class
        '''
        self.modem = modem

    def _build_ds_metrics(self, downstream):
        ds_metrics_lock = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'lock']),
            'Lock status of downstream channel, bool.',
            labels=XB7Collector.LABELS
        )
        ds_metrics_freq = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'freq']),
            'Frequency of downstream channel in MHz.',
            labels=XB7Collector.LABELS
        )
        ds_metrics_snr = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'snr']),
            'SNR of downstream channel in dB.',
            labels=XB7Collector.LABELS
        )
        ds_metrics_power = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'power']),
            'Power level of channel, in dBmV.',
            labels=XB7Collector.LABELS
        )
        # ds_metrics_mod = GaugeMetricFamily(
        #     '_'.join([XB7Collector.KEY_PREFIX, 'mod']),
        #     'Modulation of the downstream channel, string.',
        #     labels=XB7Collector.LABELS
        # )

        for ds in downstream:
            ds_metrics_lock.add_metric([self.modem.ip_address, str(ds.index)], 1 if ds.lock == "Locked" else 0)
            ds_metrics_freq.add_metric([self.modem.ip_address, str(ds.index)], ds.freq)
            ds_metrics_snr.add_metric([self.modem.ip_address, str(ds.index)], ds.snr)
            ds_metrics_power.add_metric([self.modem.ip_address, str(ds.index)], ds.power)
        #     ds_metrics_mod.add_metric([self.modem.ip_address, str(ds.index)], ds.mod)

        yield ds_metrics_lock
        yield ds_metrics_freq
        yield ds_metrics_snr
        yield ds_metrics_power
        # yield ds_metrics_mod

    def _build_us_metrics(self, upstream):
        us_metrics_lock = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'us', 'lock']),
            'Lock status of upstrea channel, bool.',
            labels=XB7Collector.LABELS
        )
        us_metrics_freq = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'us', 'freq']),
            'Frequency of upstream channel in MHz.',
            labels=XB7Collector.LABELS
        )
        us_metrics_symbol = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'us', 'symbol']),
            'Symbol rate of upstream channel.',
            labels=XB7Collector.LABELS
        )
        us_metrics_power = GaugeMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'us', 'power']),
            'Power level of channel, in dBmV.',
            labels=XB7Collector.LABELS
        )
        # us_metrics_mod = GaugeMetricFamily(
        #     '_'.join([XB7Collector.KEY_PREFIX, 'mod']),
        #     'Modulation of the upstream channel, string.',
        #     labels=XB7Collector.LABELS
        # )
        # us_metrics_c_type = GaugeMetricFamily(
        #     '_'.join([XB7Collector.KEY_PREFIX, 'c_type']),
        #     'Channel type of the upstream channel, string.',
        #     labels=XB7Collector.LABELS
        # )

        for us in upstream:
            us_metrics_lock.add_metric([self.modem.ip_address, str(us.index)], 1 if us.lock == "Locked" else 0)
            us_metrics_freq.add_metric([self.modem.ip_address, str(us.index)], us.freq)
            us_metrics_symbol.add_metric([self.modem.ip_address, str(us.index)], us.symbol)
            us_metrics_power.add_metric([self.modem.ip_address, str(us.index)], us.power)
        #     us_metrics_mod.add_metric([self.modem.ip_address, str(us.index)], us.mod)
        #     us_metrics_c_type.add_metric([self.modem.ip_address, str(us.index)], us.c_type)

        yield us_metrics_lock
        yield us_metrics_freq
        yield us_metrics_symbol
        yield us_metrics_power
        # yield us_metrics_mod
        # yield us_metrics_c_type

    def _build_cme_metrics(self, cm_errors):
        cme_metrics_unerrored = CounterMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'unerrored']),
            'Unerrored Codewords of downstream channel, int.',
            labels=XB7Collector.LABELS
        )
        cme_metrics_correctable = CounterMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'correctable']),
            'Unerrored Codewords of downstream channel, int.',
            labels=XB7Collector.LABELS
        )
        cme_metrics_uncorrectable = CounterMetricFamily(
            '_'.join([XB7Collector.KEY_PREFIX, 'ds', 'uncorrectable']),
            'Unerrored Codewords of downstream channel, int.',
            labels=XB7Collector.LABELS
        )

        for cme in cm_errors:
            cme_metrics_unerrored.add_metric([self.modem.ip_address, str(cme.index)], cme.unerrored)
            cme_metrics_correctable.add_metric([self.modem.ip_address, str(cme.index)], cme.correctable)
            cme_metrics_uncorrectable.add_metric([self.modem.ip_address, str(cme.index)], cme.uncorrectable)

        yield cme_metrics_unerrored
        yield cme_metrics_correctable
        yield cme_metrics_uncorrectable

    def collect(self):
        LOG.info('New collection request.')

        (downstream, upstream, cm_errors) = self.modem.get_html_stats()

        return itertools.chain(
            self._build_ds_metrics(downstream),
            self._build_us_metrics(upstream),
            self._build_cme_metrics(cm_errors)
        )


def _handle_debug(debug):
    '''Turn on debugging if asked otherwise INFO default'''
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s (%(filename)s:%(lineno)d)',
        level=log_level,
    )

@click.command()
@click.option('-i', '--ip_address', default='10.0.0.1', help='IP address of XB7.')
@click.option('-u', '--username', default='admin', help='Username to auth XB7 with.')
@click.option('-P', '--password', default='password', help='Password to auth XB7 with.')
@click.option('-p', '--port', default=DEFAULT_PORT, type=int, help='Port to run prometheus collector on.')
@click.option('-d', '--debug', is_flag=True)
def main(ip_address, username, password, port, debug):
    _handle_debug(debug)

    # Create modem object for collector to use
    modem = XB7(ip_address, username, password)

    # Start metrics server
    LOG.info(f'Starting server on port {port}')
    start_http_server(port)

    # Register XB7 collector
    REGISTRY.register(XB7Collector(modem))
    LOG.info(f'xb7 prometheus exporter - listening on {port}')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOG.info('Shutting down ...')
    return 0

if __name__ == '__main__':
    main()