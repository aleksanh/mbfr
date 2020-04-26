from binary_formats.formats import EM3000, SeapathBin26, VmmMruBin, Kmbinary, SeapathBin11, sbet
import numpy as np


class fakeprogressbar(object):
    def __init__(self):
        pass

    def setValue(self, value):
        pass

    def setRange(self, min, max):
        self.min = min
        self.max = max


class DetectFormat(object):
    def __init__(self, data, mode='File'):
        self.mode = mode
        self.data = data
        self.index = 0
        self.read_lines = 10  # number of binary telegrams to read an compeare to be sure that the right format is found
        self.map = {'EM3000': self.em3000, 'Seapath_bin26': self.Seapath_bin26,
                    'KMBIN': self.km_binary()}

    def run(self):
        name = None
        func = None
        for name, func in self.map.items():
            if func():
                break
        if name is None:
            raise TypeError('No format found, specify format manualy!')
        return name

    def read_file(self, len):
        with open(self.data, 'rb') as fobj:
            self.data = fobj.read(len)
        return

    def iter(self, len):
        data = self.data[self.index:self.index+len]
        self.index = self.index+len
        if len(data) < len:
            data = None
        return data

    def em3000(self):
        # TODO: add check for status before returning true. status can only be 144, 145 or 160.
        fmt = EM3000()    # init the format in question
        data_length = 10  # nbytes to read pr datagram acording to format spesification
        if self.mode == 'File':  # aquire datagrams in stead of file path
            self.read_file(10*self.read_lines)
        else:
            if not len(self.data) == data_length*self.read_lines:  # if the user has read datagrams and not provided corect amount. avioding numpy ValueError: string size must be a multiple of element size
                raise ValueError('binary string length is wrong')
        array = fmt.read_line(self.data)
        if np.all(array['status'] == 144):  # EM3000 has only header that is definetive to check aganist.
            return True

    def Seapath_bin26(self):
        pass

    def km_binary(self):
        pass


class ReadBinFIle(object):
    def __init__(self, filename, dformat='Auto', progresbar=fakeprogressbar(), date_time=None, verbose=False):
        self.formats = {'EM3000': EM3000(), 'Seapath_bin26': SeapathBin26(),
                        'VMM_MRU_Binary': VmmMruBin(), 'KMBIN': Kmbinary()}
        self.fmt = None
        self.dformat = dformat
        self.filename = filename
        self.progess = progresbar
        self.date_time = date_time
        self.progess.setRange(0, 6)

    def run(self):
        self.progess.setValue(1)
        self.set_format()
        self.progess.setValue(2)
        raw_array = self.parse_bin()
        self.progess.setValue(3)
        converted_array = self.convert(raw_array)
        self.progess.setValue(4)
        self.make_time(converted_array)
        self.progess.setValue(5)
        packed = self.dict_packing(converted_array)
        self.progess.setValue(6)
        return packed

    def set_format(self):
        if self.dformat == 'Auto':
            self.dformat = DetectFormat(self.filename).run()
        self.fmt = self.formats[self.dformat]

    def parse_bin(self):
        return self.fmt.read_file(self.filename)

    def convert(self, array):
        if hasattr(self.fmt, 'convert_array'):
            return self.fmt.convert_array(array)
        return array

    def make_time(self, array):
        if hasattr(self.fmt, 'make_time') and self.date_time is not None:
            return self.fmt.make_time(array, self.date_time)

    def dict_packing(self, array):
        return {self.dformat: array}


