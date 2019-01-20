#!/usr/bin/env python3
#
# Generates graphs from FIO output data for various IO queue depthts
#
# Output in PNG format.
#
# Requires matplotib and numpy.
#

import os
import sys
import json
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib as mpl
from mpl_toolkits.mplot3d import axes3d
import numpy as np
import argparse
import pprint
from datetime import datetime
import math
from collections import defaultdict



class Chart(object):

    def __init__(self, data, config):
        self.data = data
        self.config = config
        d = datetime.now()
        self.date = d.strftime('%Y-%m-%d-%H:%M:%S')

    def return_unique_series(self,key):
        l = []
        for record in self.data:
            l.append(record[key])

        l = [int(x) for x in l]
        l = sorted(set(l))
        return l

    def strip_leading_zero(self, value):
        sanitized = value
        if isinstance(value,str):
            if value[0] == '0':
                sanitized = value[1]
            else:
                sanitized = value

        return sanitized


    def return_record_set(self, dataset, key, value):
        l = []
        for record in dataset:
            v = self.strip_leading_zero(str(record[key]))
            if str(v) == str(value):
                l.append(record)
        return l

    def filter_record_set(self, dataset, key, value):
        l = []
        for record in dataset:
            if record[key] == value:
                l.append(record)
        return l

    def subselect_record_set(self, dataset, keys):
        l = []
        for record in dataset:
            d = dict.fromkeys(keys)
            for key in keys:
                if record[key] is not float:
                    d[key] = self.strip_leading_zero(record[key])
            l.append(d)
        return l

    def return_latency_units(self, value):

        d = {}
        d['Nanoseconds']  = { 
                "Unit":"ns",
                "Value": Value
                }        
        d['Microseconds']  = { 
                "Unit":"us",
                "Value": Value / 1000
                }

        d['Miliseconds']  = { 
                "Unit":"ms",
                "Value": Value / 1000000
                }        

        if d['Microseconds'] > 1:
            d['Value'] = 'Microseconds'
        if d['Milisecond'] > 1:
            d['Value'] = 'Miliseconds'
        
        return d



class ThreeDee(Chart):

    def __init__(self, data, config):
        super().__init__(data, config)

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(111, projection='3d')
        self.fig.set_size_inches(15, 10)
        self.series = {}

    def generate_series(self,key,value,mode):

        recordset = self.return_record_set(key,
                                           value)
        self.series = { 'x_series': [],
                        'y_series1': [],
                        'y_series2': [],
                        'y_series3': [],
                      }

        self.series['x_series'] = self.return_unique_series(self.config['x_series'])

        for x in self.series['x_series']:
            for y in recordset:
                    if int(y[self.config['x_series']]) == int(x):
                        if mode == y['rw']:
                            self.series['y_series1'].append(round(y['iops']))       #iops
                            self.series['y_series2'].append(round(int(y['numjobs'])))       #lat

    def plot_3d(self, mode, metric):


        iodepth = self.return_unique_series('iodepth')
        numjobs = self.return_unique_series('numjobs')

        datatype=metric

        dataset = self.filter_record_set(self.data, 'rw',mode)
        mylist = []
        for x in numjobs:
            if x <= int(self.config['maxjobs']):
                dx = self.return_record_set(dataset,'numjobs', x)
                d = self.subselect_record_set(dx,['numjobs','iodepth',datatype])
                row = []
                for y in iodepth:
                    if y <= int(self.config['maxdepth']):
                        for record in d:
                            if int(record['iodepth']) == int(y):
                                row.append(record[datatype])
                mylist.append(row)
        n = np.array(mylist,dtype=float)
        if metric == 'lat':
            n = np.divide(n, 1000000)

        lx = len(n[0])
        ly = len(n[:,0])

        size = lx * 0.05 # thickness of the bar

        xpos_orig = np.arange(0,lx,1)
        ypos_orig = np.arange(0,ly,1)
    
        xpos = np.arange(0,lx,1)
        ypos = np.arange(0,ly,1)
        xpos, ypos = np.meshgrid(xpos-(size/lx), ypos-(size))

        xpos_f = xpos.flatten()   # Convert positions to 1D array
        ypos_f = ypos.flatten()
        zpos = np.zeros(lx*ly)

        dx = size * np.ones_like(zpos)
        dy = dx.copy()
        dz = n.flatten()
        values = dz / (dz.max()/1)
        cmap = plt.get_cmap('rainbow',xpos.ravel().shape[0])
        colors = cm.rainbow(values)

        self.ax1.bar3d(xpos_f,ypos_f,zpos, dx, dy, dz, color=colors)

        norm = mpl.colors.Normalize(vmin=0,vmax=dz.max())
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        self.fig.colorbar(sm) 


        float_x = [float(x) for x in (xpos_orig)]
        float_y = [float(y) for y in (ypos_orig)]

        self.ax1.w_xaxis.set_ticks(float_x)
        self.ax1.w_yaxis.set_ticks(ypos_orig)
        #self.ax1.tick_params(axis='y', direction='out', pad=5)

        self.ax1.w_xaxis.set_ticklabels(iodepth)
        self.ax1.w_yaxis.set_ticklabels(numjobs)

        # axis labels
        fontsize = 14
        self.ax1.set_xlabel('iodepth', fontsize=fontsize)
        self.ax1.set_ylabel('numjobs', fontsize=fontsize)
        self.ax1.set_zlabel(datatype,  fontsize=fontsize)

        self.ax1.xaxis.labelpad=10
        self.ax1.zaxis.labelpad=20
        self.ax1.zaxis.set_tick_params(pad = 10)
        
        # title
        plt.suptitle(self.config['title'] + " | " + mode + " | " + metric, fontsize=16, horizontalalignment='center' )

        # watermark
        max_z = (max(dz) * 0.18)
        start_y = (len(self.config['source']) * 0.1)
        self.ax1.text(lx-0.7,start_y,max_z,self.config['source'], (1,1,max_z),color='b', )


        plt.tight_layout()
        plt.savefig('3d-iops-jobs' + str(mode) + "-" + str(self.date) + '.png')
        plt.close('all')


class barChart(Chart):

    def __init__(self, data, config):
        super().__init__(data, config)

        self.fig, (self.ax1, self.ax2) = plt.subplots(
            nrows=2, gridspec_kw={'height_ratios': [7, 1]})
        self.ax3 = self.ax1.twinx()
        self.fig.set_size_inches(10, 6)

        self.series = { 'x_series': [],
                        'y_series1': [],
                        'y_series2': [],
                        'y_series3': [],
                      }

        self.config = config

        if self.config['source']:
            plt.text(1,-0.08, str(self.config['source']), ha='right', va='top',
                    transform=self.ax1.transAxes,fontsize=9)

        self.ax2.axis('off')

    def calculate_std(self):
        # Create series for Standard Deviation table.
        std = []
        for stddev in self.series['y_series3']:
            for latency in self.series['y_series2']:
                p = round((stddev / latency) * 100)
            std.append(str(p))
        self.series['y_series3'] = std


    def generate_series(self):

        dataset = self.filter_record_set(self.data, 'rw', self.config['mode'])
        recordset = self.return_record_set(dataset, self.config['fixed_metric'],
                                           self.config['fixed_value'])

        self.series['x_series'] = self.return_unique_series('iodepth')


        for x in self.series['x_series']:
            for y in recordset:
                    if int(y[self.config['x_series']]) == int(x):
                        self.series['y_series1'].append(round(y[self.config['y_series1']]))       #iops
                        self.series['y_series2'].append(round(y[self.config['y_series2']]))       #lat
                        self.series['y_series3'].append(round(y[self.config['y_series3']])) #lat_stddev

        self.calculate_std()


    def autolabel(self, rects, axis):
        for rect in rects:
            height = rect.get_height()
            if height < 10:
                formatter = '%.4f'
            else:
                formatter = '%d'
            axis.text(rect.get_x() + rect.get_width() / 2,
                      1.015 * height, formatter % height, ha='center',
                      fontsize=8)

    def create_stddev_table(self):
        table_vals = [self.series['x_series'], self.series['y_series3']]
        cols = len(self.series['x_series'])
        table = self.ax2.table(cellText=table_vals, loc='center right', rowLabels=[
                          'IO queue depth', r'$Latency\ \sigma\ \%$'],
                          colLoc='center right',
                          cellLoc='center right', colWidths=[0.05] * cols,
                          rasterized=False)
        table.scale(1,1.2)

        for key, cell in table.get_celld().items():
            cell.set_linewidth(0)


class IOL_Chart(barChart):

    def __init__(self, data, config):
        super().__init__(data, config)
        self.generate_series()
        #pprint.pprint(self.series)

    def plot_io_and_latency(self, mode, numjobs):

        self.mode = mode

        x_pos = np.arange(0, len(self.series['x_series']) * 2, 2)
        width = 0.9


        n = np.array(self.series['y_series2'],dtype=float)
        n = np.divide(n, 1000000)


        rects1 = self.ax1.bar(x_pos, self.series['y_series1'], width,
                color='#a8ed63')
        #rects2 = self.ax3.bar(x_pos + width, self.series['y_series2'], width,
        rects2 = self.ax3.bar(x_pos + width, n, width,
                        color='#34bafa')

        self.ax1.set_ylabel(self.config['y_series1_label'])
        self.ax1.set_xlabel(self.config['x_series_label'])
        self.ax3.set_ylabel(self.config['y_series2_label'])

        if self.config['title']:
            self.ax1.set_title(str(self.config['title']) + " | " + str(mode) + " | numjobs: " + str(numjobs))
        else:
            self.ax1.set_title(str(mode) + ' performance')

        self.ax1.set_xticks(x_pos + width / 2)
        self.ax1.set_xticklabels(self.series['x_series'])

        self.ax2.legend((rects1[0], rects2[0]),
                  (self.config['y_series1_label'],
                      self.config['y_series2_label']), loc='upper left',frameon=False)

        self.create_stddev_table()


        self.autolabel(rects1, self.ax1)
        self.autolabel(rects2, self.ax3)

        plt.tight_layout()
        plt.savefig(mode + '_iodepth_' + str(self.date) + '_' + str(numjobs) + '_iops_latency.png')
        plt.close('all')

    def get_sorted_mixed_list(self, unsorted_list):

        def get_type(x):
            try:
                return int(x)
            except ValueError:
                return str(x)

        sorted_list = []
        ints = []
        strings = []

        for x in unsorted_list:
            result = get_type(x)
            if isinstance(result, int):
                ints.append(result)
            else:
                strings.append(result)

        ints.sort()
        sorted_list = ints
        strings.sort()
        [sorted_list.append(x) for x in strings]
        return sorted_list


class LH_Chart(Chart):

    def sort_latency_keys(self,latency):
        placeholder = ""
        tmp = []
        for item in latency:
            if item == '>=2000':
                placeholder = ">=2000"
            else:
                tmp.append(item)

        tmp.sort(key=int)
        if(placeholder):
            tmp.append(placeholder)
        return tmp

    def sort_latency_data(self,latency_dict):

        keys = latency_dict.keys()
        values = []
        sorted_keys = self.sort_latency_keys(keys)
        for key in sorted_keys:
           values.append(latency_dict[key])
        return values 

    def generate_history_chart(self, chartdata):

        x_series = chartdata['x_series']
        y_series1 = chartdata['y_series1']
        y_series2 = chartdata['y_series2']
        depth = chartdata['iodepth']
        mode = chartdata['mode']

        coverage_ms = round(sum(y_series1), 2)
        coverage_us = round(sum(y_series2), 2)

        # Creating actual graph

        fig, (ax1, ax2) = plt.subplots(
        nrows=2, gridspec_kw={'height_ratios': [11, 1]})
        fig.set_size_inches(10, 6)

        x_pos = np.arange(0, len(x_series) * 2, 2)
        width = 1

        rects1 = ax1.bar(x_pos, y_series1, width, color='r')
        rects2 = ax1.bar(x_pos + width, y_series2, width, color='b')

        ax1.set_ylabel('Percentage of IO (ms)')
        ax1.set_xlabel(r'$Latency\ in\ ms\ or\ \mu$')
        ax1.set_title(str(self.config['title']) + " | "
                + str(mode).title() +
            ' latency histogram | IO depth ' +
            str(depth))
        ax1.set_xticks(x_pos + width / 2)
        ax1.set_xticklabels(x_series)


        if coverage_ms < 1 and coverage_ms > 0:
            coverage_ms = "<1"
        if coverage_us < 1 and coverage_us > 0:
            coverage_us = "<1"

        legend = ax2.legend((rects1[0], rects2[0]),(
            'Latency in ms (' + str(coverage_ms) + '%)',
            'Latency in us  (' + str(coverage_us) + '%)'),frameon=False,
            loc='upper left')
        ax2.axis('off')

        def autolabel(rects, axis):
            for rect in rects:
                height = rect.get_height()
                if height >= 1:
                    axis.text(rect.get_x() + rect.get_width() / 2., 1.02 *
                              height, '{}%'.format(int(height)),
                                      ha='center')
                elif height > 0:
                    axis.text(rect.get_x() + rect.get_width() /
                              2., 1.02 * height, '<1%', ha='center')

        autolabel(rects1, ax1)
        autolabel(rects2, ax1)

        plt.tight_layout()

        plt.savefig(mode + "_" + str(depth) + '_histogram.png')
        plt.close('all')


    def plot_latency_histogram(self, mode):

        latency_data = self.data

        iodepth = self.return_unique_series('iodepth')
        #numjobs = self.return_unique_series('numjobs')
        numjobs = ['1']

        datatypes = ('latency_ms','latency_us','latency_ns')

        dataset = self.filter_record_set(self.data, 'rw',mode)
        mydict = defaultdict(dict)

        #pprint.pprint(dataset)

        for datatype in datatypes:
            for x in numjobs:
                dx = self.return_record_set(dataset,'numjobs', x)
                d = self.subselect_record_set(dx,['numjobs','iodepth',datatype])
                for y in iodepth:
                    for record in d:
                        if int(record['iodepth']) == int(y):
                            mydict[datatype][int(y)] = record[datatype]
        for depth in iodepth:

            x_series = []
            y_series1 = []
            y_series2 = []
            y_series3 = []

            temporary = mydict['latency_ms'][1].keys()
            x_series = self.sort_latency_keys(temporary)
            y_series1 = self.sort_latency_data(mydict['latency_ms'][depth])
            y_series2 = self.sort_latency_data(mydict['latency_us'][depth])
            y_series3 = self.sort_latency_data(mydict['latency_ns'][depth])
            y_series2.append(0)
            y_series2.append(0)


            chart_data = {
                            'x_series': x_series, 
                            'y_series1': y_series1,
                            'y_series2': y_series2,
                            'y_series3': y_series3,
                            'iodepth': depth,
                            'numjobs': 1,
                            'mode': mode
                    
                    }
            
            self.generate_history_chart(chart_data)


class benchmark(object):

    def __init__(self, settings):
        self.directory = settings['input_directory']
        self.data = self.getDataSet()
        self.settings = settings
        self.stats = []

    def listJsonFiles(self, directory):
        absolute_dir = os.path.abspath(directory)
        files = os.listdir(absolute_dir)
        json_files = []
        for f in files:
            if f.endswith(".json"):
                json_files.append(os.path.join(absolute_dir, f))

        return json_files

    def getJSONFileStats(self, filename):
        with open(filename) as json_data:
            d = json.load(json_data)

        return d

    def getDataSet(self):
        d = []
        for f in self.listJsonFiles(self.directory):
            d.append(self.getJSONFileStats(f))

        return d

    def get_nested_value(self, dictionary, key):
        for item in key:
            dictionary = dictionary[item]
        return dictionary


    def get_json_mapping(self,mode):
        root =       ['jobs',0]
        jobOptions = root + ['job options']
        data =       root + [mode]

        dictionary = {
            'iodepth': (jobOptions + ['iodepth']),
            'numjobs': (jobOptions + ['numjobs']),
            'rw': (jobOptions + ['rw']),
            'iops': (data + ['iops']),
            'lat_ns': (data + ['lat_ns','mean']),
            #'lat': (data + ['lat','mean']),
            'lat_stddev': (data + ['lat_ns','stddev']),
            'latency_ms': (root + ['latency_ms']),
            'latency_us': (root + ['latency_us']),
            'latency_ns': (root + ['latency_ns'])
        }

        return dictionary

    def getStats(self):
        stats = []
        for record in self.data:
            #pprint.pprint(record)
            mode = self.get_nested_value(record,('jobs',0,'job options','rw'))[4:]
            m = self.get_json_mapping(mode)
            #pprint.pprint(m)
            row = {'iodepth': self.get_nested_value(record,m['iodepth']),
                   'numjobs': self.get_nested_value(record,m['numjobs']),
                        'rw': self.get_nested_value(record,m['rw']),
                      'iops': self.get_nested_value(record,m['iops']),
                       'lat': self.get_nested_value(record,m['lat_ns']),
                'lat_stddev': self.get_nested_value(record,m['lat_stddev']),
                'latency_ms': self.get_nested_value(record,m['latency_ms']),
                'latency_us': self.get_nested_value(record,m['latency_us']),
                'latency_ns': self.get_nested_value(record,m['latency_ns'])}
            stats.append(row)
        self.stats = stats

    def filterStats(self,key,value):
        l = []
        for item in self.stats:
            if item[key] == value:
                l.append(item)
        return l

    def chart_3d_iops_numjobs(self, mode, metric):
        self.getStats()
        config = {}
        config['mode'] = mode
        config['source'] = self.settings['source']
        config['title']  = self.settings['title']
        config['fixed_metric'] = 'numjobs'
        config['fixed_value'] = 1
        config['x_series']  = 'iodepth'
        config['x_series_label'] = 'I/O Depth'
        config['y_series1'] = 'iops'
        config['y_series1_label'] = 'IOP/s'
        config['y_series2'] = 'lat'
        config['y_series2_label'] = r'$Latency\ in\ ms'
        config['y_series3'] = 'lat_stddev'
        config['maxjobs'] = self.settings['maxjobs']
        config['maxdepth'] = self.settings['maxdepth']
        c = ThreeDee(self.stats, config)
        c.plot_3d(config['mode'], metric)

    def chart_iops_latency(self, mode):
        self.getStats()
        config = {}
        config['mode'] = mode
        config['source'] = self.settings['source']
        config['title']  = self.settings['title']
        config['fixed_metric'] = 'numjobs'
        config['fixed_value'] = self.settings['numjobs']
        config['x_series']  = 'iodepth'
        config['x_series_label'] = 'I/O Depth'
        config['y_series1'] = 'iops'
        config['y_series1_label'] = 'IOP/s'
        config['y_series2'] = 'lat'
        config['y_series2_label'] = r'Latency in ms'
        config['y_series3'] = 'lat_stddev'
        c = IOL_Chart(self.stats, config)
        c.plot_io_and_latency(config['mode'],self.settings['numjobs'])


    def chart_latency_histogram(self, mode):
        self.getStats()
        config = {}
        config['mode'] = mode
        config['source'] = self.settings['source']
        config['title']  = self.settings['title']
        config['fixed_metric'] = 'numjobs'
        config['fixed_value'] = 1
        config['x_series']  = 'iodepth'
        config['x_series_label'] = 'I/O Depth'
        config['y_series1'] = 'iops'
        config['y_series1_label'] = 'IOP/s'
        config['y_series2'] = 'lat'
        config['y_series2_label'] = r'$Latency\ in\ \mu$'
        config['y_series3'] = 'lat_stddev'
        c = LH_Chart(self.stats,self.settings)
        c.plot_latency_histogram(mode)


def set_arguments():

    parser = argparse.ArgumentParser(description='Convert FIO JSON output \
            to charts')

    ag = parser.add_argument_group(title="Generic Settings")
    ag.add_argument("-i", "--input-directory", help="input directory where\
            JSON files can be found" )
    ag.add_argument("-t", "--title", help="specifies title to use in charts")
    ag.add_argument("-s", "--source", help="Author" )
    ag.add_argument("-L", "--latency_iops", action='store_true', help="\
            generate latency + iops chart" )
    ag.add_argument("-H", "--histogram", action='store_true', help="\
            generate latency histogram per queue depth" )
    ag.add_argument("-D", "--maxdepth", help="\
            maximum queue depth to graph")
    ag.add_argument("-J", "--maxjobs", help="\
            maximum numjobs to graph")
    ag.add_argument("-n", "--numjobs", help="\
            species for which numjob parameter you want graphs to be generated")

    return parser


def main():
    settings = {}

    parser = set_arguments()

    try:
        args = parser.parse_args()
    except OSError:
        parser.print_help()
        sys.exit(1)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    settings = vars(args)

    b = benchmark(settings)

    if settings['latency_iops']:
        b.chart_3d_iops_numjobs('randread','iops')
        #b.chart_3d_iops_numjobs('randwrite','iops')
        #b.chart_3d_iops_numjobs('randread','lat')
        #b.chart_3d_iops_numjobs('randwrite','lat')
        #b.chart_iops_latency('randread')
        #b.chart_iops_latency('randwrite')

    if settings['histogram']:
        b.chart_latency_histogram('randread')
        b.chart_latency_histogram('randwrite')

    if not settings['histogram'] and not settings['latency_iops']:
        parser.print_help()
        print("Specify -L, -H or both")
        exit(1)

if __name__ == "__main__":
    main()