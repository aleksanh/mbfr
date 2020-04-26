import numpy as np
import datetime
from stx_functions.functions import conv_head


class BinaryAbc(object):
    '''
    the binary abstract base class is implemented to ensure that all binary format classes have the
     correct minimum functions needed by the top read_file class and serial / udp read classes.
    '''

    def __init__(self):
        self.dtype_erect()
        self.struct_erect()

    def dtype_erect(self):
        pass

    def struct_erect(self):
        pass

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self.dtype)
        return array

    def read_line(self, data, convert=False):
        array = np.fromstring(data, dtype=self.dtype)
        # print(org_array, len(org_array))
        if convert:
            array = self.convert_array(array)
        return array

    def convert_array(self, array):
        return array

    def calcEpoch(self, Year, Month, Day, HH, mm, ss):
        dt = datetime.datetime(1970, 1, 1)
        return (datetime.datetime(Year, Month, Day, HH, mm, ss) - dt).total_seconds()


class EM3000(BinaryAbc):
    '''
    EM3000 binary format is an aincient format made by Simarad Horten for early subsea equipment,
    and should be conisdered deprechiated as it do not contain time or checksum.
    an time aporoximation can be added after using convert array by runing make time. date_time tuple should be:
    year, month, day, hour, minute, second and interval of datagrams. date time is specified when first datagram is
    sampled.
    '''
    def __init__(self):
        super(EM3000, self).__init__()
        self.dtype = [('status', '<u1'), ('header', '<u1'), ('Roll', '<i2'),
                      ('Pitch', '<i2'), ('Heave', '<i2'), ('Heading', '<u2')]

        self.new_dtype = [('status', '<u1'), ('header', '<u1'), ('Roll', '<f4'),
                          ('Pitch', '<f4'), ('Heave', '<f4'), ('Heading', '<f4'), ('utc_time', '<f8')]

    def convert_array(self, array):
        new_array = np.zeros((len(array)), dtype=self.new_dtype)
        names = ['Roll', 'Pitch', 'Heading', 'Heave']
        for item in self.new_dtype:
            name = item[0]
            if name in names:
                new_array[name] = array[name] * 0.01
            else:
                try:
                    new_array[name] = array[name]
                except ValueError:
                    continue
        for old, new in {144: 0, 145: 1, 160: 2}.items():
            new_array['status'][np.where(new_array['status'] == old)] = new
        return new_array

    def make_time(self, array, date_time):
        '''
        Some binary formats do not have a time stamp, or lake som time information to give a full
        posix time stamp, make sure that your format parser makes a full posix time before returning the parsed result.
        :return:
        '''
        year = date_time[0]
        month = date_time[1]
        day = date_time[2]
        hour = date_time[3]
        minute = date_time[4]
        second = date_time[5]
        interval = date_time[6]
        init_time = self.calcEpoch(year, month, day, hour, minute, second)
        for x in range(len(array)):
            array['utc_time'][x] = init_time
            init_time += interval
        return


class SeapathBin11(object):
    def __init__(self):
        self.sp_dtype = [('Header1', '>u1'), ('utc_time', '>i4'),  ('utc_fraction', '>u1'),
                         ('latitude', '>i4'), ('longitude', '>i4'), ('height', '>i4'), ('heave', '>i2'),
                         ('north_vel', '>i2'), ('east_vel', '>i2'), ('down_vel', '>i2'), ('roll', '>i2'), ('pitch','>i2'),
                         ('heading', '>u2'), ('roll_rate', '>i2'), ('pitch_rate', '>i2'), ('yaw_rate', '>i2'),
                         ('status', '>u2'), ('checksum', '>u2')]

        self.new_dtype = [('Header1', '>u1'), ('utc_time', '>f8'),
                         ('latitude', '>f8'), ('longitude', '>f8'), ('height', '>f8'), ('heave', '>f8'),
                         ('north_vel', '>f8'), ('east_vel', '>f8'), ('down_vel', '>f8'), ('roll', '>f4'), ('pitch','>f4'),
                         ('heading', '>f4'), ('roll_rate', '>f4'), ('pitch_rate', '>f4'), ('yaw_rate', '>f4'),
                         ('status', '>u2'), ('checksum', '>u2')]

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self.sp_dtype)
        return array

    def read_line(self, data):
        org_array = np.fromstring(data, dtype=self.sp_dtype)
        #print(org_array, len(org_array))
        converted_array = self.convert_array(org_array)
        return converted_array

    def convert_array(self, array):
        new_array = np.zeros((len(array)), dtype=self.new_dtype)
        for item in self.new_dtype:
            name = item[0]
            try:
                new_array[name] = array[name]
            except ValueError:
                continue
        new_array['latitude'] = self.conv_pos(array['latitude'])
        new_array['longitude'] = self.conv_pos(array['longitude'])
        new_array['height'] = self.conv_cm(array['height'])
        new_array['heave'] = self.conv_cm(array['heave']) * -1
        new_array['north_vel'] = self.conv_cm(array['north_vel'])
        new_array['east_vel'] = self.conv_cm(array['east_vel'])
        new_array['down_vel'] = self.conv_cm(array['down_vel'])
        new_array['roll'] = self.conv_atti(array['roll'])
        new_array['pitch'] = self.conv_atti(array['pitch'])
        new_array['heading'] = self.conv_heading(array['heading'])
        new_array['roll_rate'] = self.conv_atti(array['roll_rate'])
        new_array['pitch_rate'] = self.conv_atti(array['pitch_rate'])
        new_array['yaw_rate'] = self.conv_atti(array['yaw_rate'])
        new_array['utc_time'] = self.conv_time(array['utc_time'], array['utc_fraction'])
        return new_array

    def conv_pos(self, value):
        return value * (90.0 / 2 ** 30)

    def conv_heading(self, value):
        return value * (360.0 / 2 ** 16)

    def conv_time(self, posix, fraction):
        return posix + (fraction * 0.0001)

    def conv_cm(self, value):
        return value * 0.01

    def conv_atti(self, value):
        return value * (90.0 / 2 ** 14)


class SeapathBin26(object):
    def __init__(self):
        self.sp_dtype = [('Header1', '>u1'), ('Header2', '>u1'), ('utc_time', '>i4'),  ('utc_fraction','>u2'),
                         ('latitude', '>i4'), ('longitude', '>i4'), ('height', '>i4'), ('heave', '>i2'),
                         ('north_vel', '>i2'), ('east_vel', '>i2'), ('down_vel', '>i2'), ('roll', '>i2'), ('pitch','>i2'),
                         ('heading', '>u2'), ('roll_rate', '>i2'), ('pitch_rate', '>i2'), ('yaw_rate', '>i2'),
                         ('delayed_heave_time', '>i4'), ('delayed_heave_frac', '>u2'), ('delayed_heave', '>i2'),
                         ('status', '>u2'), ('checksum', '>u2')]

        self.new_dtype = [('Header1', '>u1'), ('Header2', '>u1'), ('utc_time', '>f8'),
                         ('latitude', '>f8'), ('longitude', '>f8'), ('height', '>f8'), ('heave', '>f8'),
                         ('north_vel', '>f8'), ('east_vel', '>f8'), ('down_vel', '>f8'), ('roll', '>f4'), ('pitch','>f4'),
                         ('heading', '>f4'), ('roll_rate', '>f4'), ('pitch_rate', '>f4'), ('yaw_rate', '>f4'),
                         ('delayed_heave_time', '>f8'), ('delayed_heave', '>f4'), ('status', '>u2'), ('checksum', '>u2')]

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self.sp_dtype)
        return array

    def read_line(self, data):
        org_array = np.fromstring(data, dtype=self.sp_dtype)
        #print(org_array, len(org_array))
        converted_array = self.convert_array(org_array)
        return converted_array

    def convert_array(self, array):
        new_array = np.zeros((len(array)), dtype=self.new_dtype)
        for item in self.new_dtype:
            name = item[0]
            try:
                new_array[name] = array[name]
            except ValueError:
                continue
        new_array['latitude'] = self.conv_pos(array['latitude'])
        new_array['longitude'] = self.conv_pos(array['longitude'])
        new_array['height'] = self.conv_cm(array['height'])
        new_array['heave'] = self.conv_cm(array['heave']) * -1
        new_array['north_vel'] = self.conv_cm(array['north_vel'])
        new_array['east_vel'] = self.conv_cm(array['east_vel'])
        new_array['down_vel'] = self.conv_cm(array['down_vel'])
        new_array['roll'] = self.conv_atti(array['roll'])
        new_array['pitch'] = self.conv_atti(array['pitch'])
        new_array['heading'] = self.conv_heading(array['heading'])
        new_array['roll_rate'] = self.conv_atti(array['roll_rate'])
        new_array['pitch_rate'] = self.conv_atti(array['pitch_rate'])
        new_array['yaw_rate'] = self.conv_atti(array['yaw_rate'])
        new_array['delayed_heave'] = self.conv_cm(array['delayed_heave']) * -1
        new_array['delayed_heave_time'] = self.conv_time(array['delayed_heave_time'], array['delayed_heave_frac'])
        new_array['utc_time'] = self.conv_time(array['utc_time'], array['utc_fraction'])
        return new_array

    def conv_pos(self, value):
        return value * (90.0 / 2 ** 30)

    def conv_heading(self, value):
        return value * (360.0 / 2 ** 16)

    def conv_time(self, posix, fraction):
        return posix + (fraction * 0.0001)

    def conv_cm(self, value):
        return value * 0.01

    def conv_atti(self, value):
        return value * (90.0 / 2 ** 14)


class VmmMruBin(object):
    def __init__(self):
        self._dtype = [('Header', '>u1'), ('Length', '>u1'), ('token', '>u1'),  ('Roll', '>f4'), ('Pitch', '>f4'),
                       ('Yaw', '>f4'), ('Angular_Velocity_Roll', '>f4'), ('Angular_Velocity_Pitch', '>f4'),
                       ('Angular_Velocity_Yaw', '>f4'), ('Linear_Velocity_Forward', '>f4'),
                       ('Linear_Velocity_Starboard', '>f4'), ('Linear_Velocity_Down', '>f4'),
                       ('Linear_Acceleration_Forward','>f4'), ('Linear_Acceleration_Starboard','>f4'),
                       ('Linear_Acceleration_Down', '>f4'), ('fraction_time', '>i4'), ('checksum', '>u1')]

        self.new_dtype = [('utc_time', '<f8'), ('Header', '>u1'), ('Length', '>u1'), ('token', '>u1'), ('Roll', '>f4'), ('Pitch', '>f4'),
                   ('Yaw', '>f4'), ('Angular_Velocity_Roll', '>f4'), ('Angular_Velocity_Pitch', '>f4'),
                   ('Angular_Velocity_Yaw', '>f4'), ('Linear_Velocity_Forward', '>f4'),
                   ('Linear_Velocity_Starboard', '>f4'), ('Linear_Velocity_Down', '>f4'),
                   ('Linear_Acceleration_Forward', '>f4'), ('Linear_Acceleration_Starboard', '>f4'),
                   ('Linear_Acceleration_Down', '>f4'), ('fraction_time', '>i4'), ('checksum', '>u1')]

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self._dtype)
        return array

    def convert_array(self, array):
        new_array = array.astype(self.new_dtype)
        new_array['Roll'] = np.rad2deg(array['Roll'])
        new_array['Pitch'] = np.rad2deg(array['Pitch'])
        new_array['Yaw'] = np.rad2deg(array['Yaw'])
        new_array['Angular_Velocity_Roll'] = np.rad2deg(array['Angular_Velocity_Roll'])
        new_array['Angular_Velocity_Pitch'] = np.rad2deg(array['Angular_Velocity_Pitch'])
        new_array['Angular_Velocity_Yaw'] = np.rad2deg(array['Angular_Velocity_Yaw'])
        return new_array

    def make_time(self, array, date_time):
        year = date_time[0]
        month = date_time[1]
        day = date_time[2]
        hour = date_time[3]
        minute = date_time[4]
        second = date_time[5]
        indexes = np.where(np.diff(array['fraction_time']) < 0)[0]
        init_time = self.calcEpoch(year, month, day, hour, minute, second)
        array['utc_time'] = array['fraction_time'] * 1e-9 + init_time
        for x in range(len(indexes)):
            st = indexes[x] + 1
            try:
                en = indexes[x + 1] + 1
            except IndexError:
                en = len(array)
            array['utc_time'][st:en] += x + 1
        return

    def calcEpoch(self, YY, MM, DD, HH, mm, ss):
        dt = datetime.datetime(1970, 1, 1)
        return (datetime.datetime(YY, MM, DD, HH, mm, ss) - dt).total_seconds()


class Kmbinary(object):
    def __init__(self):
        # dtype to construct a array that exactly matches the binary format
        self.sp_dtype = [('id', '<a4'), ('length', '<u2'), ('version', '<u2'),  ('utc_seconds', '<u4'),
                         ('utc_nanos', '<u4'), ('status', '<u4'),
                         ('latitude', '<f8'), ('longitude', '<f8'), ('height', '<f4'), ('roll', '<f4'), ('pitch', '<f4'),
                         ('heading', '<f4'), ('heave', '<f4'), ('roll_rate', '<f4'), ('pitch_rate', '<f4'),
                         ('yaw_rate', '<f4'), ('north_vel', '<f4'), ('east_vel', '<f4'), ('down_vel', '<f4'),
                         ('latitude_error', '<f4'), ('longitude_error', '<f4'), ('height_error', '<f4'),
                         ('roll_error', '<f4'), ('pitch_error', '<f4'), ('heading_error', '<f4'), ('heave_error', '<f4'),
                         ('north_acceleration', '<f4'), ('east_acceleration', '<f4'), ('down_acceleration', '<f4'),
                         ('delayed_seconds', '<u4'), ('delayed_nanos', '<u4'), ('delayed_heave', '<f4')]
        # dtype that is designed to fit som conversion of certain data points, ie time and time fraction to epoch time
        self.new_dtype = [('utc_time', '<f8'), ('latitude', '<f8'), ('longitude', '<f8'), ('height', '<f4'),
                             ('roll', '<f4'), ('pitch', '<f4'), ('heading', '<f4'), ('heave', '<f4'),
                             ('roll_rate', '<f4'), ('pitch_rate', '<f4'), ('yaw_rate', '<f4'), ('north_vel', '<f4'),
                             ('east_vel', '<f4'), ('down_vel', '<f4'), ('latitude_error', '<f4'),
                             ('longitude_error', '<f4'), ('height_error', '<f4'), ('roll_error', '<f4'),
                             ('pitch_error', '<f4'), ('heading_error', '<f4'), ('heave_error', '<f4'),
                             ('north_acceleration', '<f4'), ('east_acceleration', '<f4'), ('down_acceleration', '<f4'),
                             ('delayed_time', '<f8'), ('delayed_heave', '<f4'), ('status_horiz_pos_vel', '<u4'),
                             ('status_roll_pitch', '<u4'), ('status_heading', '<u4'), ('status_heave_vec', '<u4'),
                             ('status_acceleration', '<u4'), ('status_delayed', '<u4')]

    def isKthBitSet(self, n, k):
        if n & (1 << (k - 1)):
            return True
        else:
            return False

    def mod_status(self, status, array):
        names = ['status_horiz_pos_vel', 'status_roll_pitch', 'status_heading', 
                 'status_heave_vec', 'status_acceleration',
                 'status_delayed']*2
        uniq = np.unique(status)
        print(uniq, len(uniq))
        for i in uniq:
            where = np.where(status == i)[0]
            for x, name in zip([1,2,3,4,5,16,17,18,19,20,21], names):
                if self.isKthBitSet(i, x):
                    if x <= 6:
                        v = 2
                    if x >= 6:
                        v = 1
                    array[name][where] = v

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self.sp_dtype)
        return array

    def read_line(self, data):
        org_array = np.fromstring(data, dtype=self.sp_dtype)
        converted_array = self.convert_array(org_array)
        return converted_array

    def convert_array(self, array, modtime=False):
        new_array = np.zeros((len(array)), dtype=self.new_dtype)
        for item in self.new_dtype:
            name = item[0]
            try:
                new_array[name] = array[name]
            except ValueError:
                continue
        new_array['utc_time'] = self.conv_time(array['utc_seconds'], array['utc_nanos'])
        new_array['delayed_time'] = self.conv_time(array['delayed_seconds'], array['delayed_nanos'])
        self.mod_status(array['status'], new_array)
        return new_array

    def conv_time(self, epoch, nanofrac):
        return epoch + (nanofrac / 10.0**9)


class sbet(object):
    def __init__(self):
        # dtype to construct a array that exactly matches the binary format
        self.dtype = [('utc_time', 'f8'), ('latitude', 'f8'), ('longitude', 'f8'), ('height', 'f8'),
                      ('x_velocity', 'f8'),('y_velocity', 'f8'), ('z_velocity', 'f8'), ('roll', 'f8'), ('pitch', 'f8'),
                      ('heading', 'f8'),('wander_angle', 'f8'), ('x_acceleration', 'f8'), ('y_acceleration', 'f8'),
                      ('z_acceleration', 'f8'),('x_angular_rate', 'f8'), ('y_angular_rate', 'f8'), ('z_angular_rate', 'f8')]

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self.dtype)
        array = self.convert_rad(array)
        return array


    def convert_rad(self, array):
        for name in ['latitude', 'longitude', 'roll', 'pitch', 'x_angular_rate', 'y_angular_rate', 'z_angular_rate']:
            array[name] = np.rad2deg(array[name])
        array['heading'] = conv_head(array['heading'])
        return array


class PfreeHeave(object):
    def __init__(self):
        self.dtype = [('Header1', '>u1'), ('Header2', '>u1'), ('posix', '>i4'),  ('fraction', '>u2'),
                      ('heave', '>i2'), ('status', '>u1'), ('checksum', '>u2')]

        self.conv_dtype = [('Header1', '>u1'), ('Header2', '>u1'), ('utc_time', '>f8'),
                           ('heave', '>f4'), ('status', '>u1'), ('checksum', '>u2')]

    def read_file(self, filename):
        array = np.fromfile(filename, dtype=self.dtype)
        return array

    def read_line(self, data):
        org_array = np.fromstring(data, dtype=self.dtype)
        #print(org_array, len(org_array))
        converted_array = self.convert_array(org_array)
        return converted_array

    def convert_array(self, array):
        new_array = np.zeros((len(array)), dtype=self.conv_dtype)
        for item in self.conv_dtype:
            name = item[0]
            try:
                new_array[name] = array[name]
            except ValueError:
                continue
        new_array['utc_time'] = array['posix'] + (array['fraction'] / 10.0**4)
        new_array['heave'] = array['heave'] * 0.01

        return new_array
