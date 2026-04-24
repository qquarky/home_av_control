"""
This file is for communicating with Extron AV devices via telnet SIS
commands.
"""

import base64
import enum
import os
import telnetlib
import time

import requests


class ExtronDevice(enum.Enum):
    SW = enum.auto()
    DXP = enum.auto()
    ISS = enum.auto()
    ANN = enum.auto()
    SMP = enum.auto()
    MGP = enum.auto()
    XTP = enum.auto()
    IN1804 = enum.auto()


class ExtronClient:
    ESC = "\x1B"  # Expected starting character for SIS commands

    def __init__(self, host, password=None):
        if password is None:
            self.password = os.getenv("extron_password")
            if self.password is None:
                raise Exception("Please set extron_password env variable")
        else:
            self.password = password
        self.host = host
        self.client = None
        self.device_type = None
        self.logged_in = False
        self.last_client_usage = time.time() - 60
        self.image_filename = None

    def log_in(self):
        """
        Log into the device and store its type (ISS, SW, DXP, XTP, etc.)
        """
        print(
            "Logged in:",
            self.logged_in,
            time.time() - self.last_client_usage
        )
        if(
                time.time() - self.last_client_usage > 30
                or not self.logged_in
        ):
            self.client = telnetlib.Telnet(self.host)
            self.device_type = None

            while self.device_type is None:
                login_msg = self.read_input()
                print("Login", login_msg)
                if "DXP" in login_msg:
                    self.device_type = ExtronDevice.DXP
                    break
                elif "SW" in login_msg:
                    self.device_type = ExtronDevice.SW
                    break
                elif "ISS" in login_msg:
                    self.device_type = ExtronDevice.ISS
                    break
                elif "ANNOTATOR" in login_msg:
                    self.device_type = ExtronDevice.ANN
                    break
                elif "SMP" in login_msg:
                    self.device_type = ExtronDevice.SMP
                    break
                elif "MGP" in login_msg:
                    self.device_type = ExtronDevice.MGP
                    break
                elif "XTP" in login_msg:
                    self.device_type = ExtronDevice.XTP
                elif "IN1804" in login_msg:
                    self.device_type = ExtronDevice.IN1804

            if hasattr(self, "password") and self.password:
                self.client.read_until(b"Password:")
                self.client.write(self.password.encode("ascii") + b"\n")
                self.expect()
            self.last_client_usage = time.time()
            self.logged_in = True

    def change_input(self, input_id, output_id=None):
        """
        Changes the active input (and output, if supported) of
        the Extron device
        """
        if self.device_type in [
            ExtronDevice.DXP,
            ExtronDevice.ISS,
            ExtronDevice.XTP
        ]:
            if not isinstance(output_id, int):
                raise ValueError(
                    "Devices with multiple outputs expect an output id"
                )
            cmd = "{}*{}!".format(input_id, output_id).encode("ascii") + b"\n"
        else:
            cmd = "{}!".format(input_id).encode("ascii") + b"\n"
        self.read_input()
        self.client.write(cmd)
        self.last_client_usage = time.time()
        output = self.expect()

        if self.device_type == ExtronDevice.ISS:
            self.take()
            self.client.write(cmd)
            self.last_client_usage = time.time()
            output = self.expect()
        return output

    def cec_on(self, input=1):
        """
        Send the CEC ON command to the given input
        Note that the Extron device must support CEC like
        the IN1804, SW2/4/6/8 HD 4K Plus, etc.
        """
        cmd = '{}O{}*"PwrOn"DCEC\r\n'.format(
            self.ESC, input
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def cec_off(self, input=1):
        """
        Send the CEC OFF command to the given input
        Note that the Extron device must support CEC like
        the IN1804, SW2/4/6/8 HD 4K Plus, etc.
        """
        cmd = '{}O{}*"PwrOff"DCEC\r\n'.format(
            self.ESC, input
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def cec_input(self, extron_output_id, cec_input_id=1):
        """
        Change the consumer device's active source to cec_input_id via CEC.
        (Usually 1/2/3 correspond to HDMI1/HDMI2/HDMI3.
        Note that the Extron device must support CEC like
        the IN1804, SW2/4/6/8 HD 4K Plus, etc.
        """
        cmd = "{}O{}*15*%82%{}0%00DCEC\r\n".format(
            self.ESC, extron_output_id, cec_input_id
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def capture_image(self):
        """
        This will capture an image of the active display on an MGP 641 xi
        """
        self.image_filename = "/Graphics/{}.bmp".format(time.time())
        mgp_save = "0*{}MF".format(self.image_filename)
        cmd = "{}{}\r\n".format(
            self.ESC, mgp_save
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def list_files(self):
        """
        This will return a list of files that are stored on the
        internal MGP 641 xi's storage
        """
        mgp_list = "LF"
        cmd = '{}{}\r\n'.format(
            self.ESC, mgp_list
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()

        result = self.expect()
        files = result[-1].decode()
        screen_shots = []
        for file in files.split("\r\n"):
            if file.startswith("Graphics/"):
                screen_shots.append(file.split(" ")[0])
        return screen_shots

    def save_image(self, delete=False):
        """
        This will download a file from the MGP 641 xi's internal
        storage
        """
        url = f"https://{self.host}/api/login"
        headers = {
            "Authorization": "Basic {}".format(
                base64.b64encode(
                    f"admin:{self.password}".encode()
                ).decode()
            )
        }
        params = {
            "rnd": int(time.time() * 1000)
        }
        session = requests.Session()

        response = session.post(
            url,
            headers=headers,
            params=params,
            verify=False
        )
        if response.status_code == 200:
            file_response = session.get(
                f"https://{self.host}{self.image_filename}",
                verify=False
            )

            with open(os.path.basename(self.image_filename), "wb") as ff:
                ff.write(file_response.content)
        if delete:
            self.delete_image()

    def delete_image(self, filename=None):
        """
        This will delete a file from the MGP 641 xi's internal storage
        """
        if filename is None:
            filename = self.image_filename

        mgp_save = "{}EF".format(filename)
        cmd = '{}{}\r\n'.format(
            self.ESC, mgp_save
        ).encode("ascii") + b"\n"

        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def start_recording(self):
        """
        Start recording the active display on an SMP111/351/352/401
        """
        cmd = '{}Y1RCDR\r\n'.format(
            self.ESC
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def stop_recording(self):
        """
        Stop recording the active display on an SMP111/351/352/401
        :return:
        """
        cmd = '{}Y0RCDR\r\n'.format(
            self.ESC
        ).encode("ascii") + b"\n"
        self.client.write(cmd)
        self.last_client_usage = time.time()
        return self.expect()

    def take(self):
        """
        Switch the preview/active input on an ISS 602
        """
        self.client.write(b"%")
        self.last_client_usage = time.time()
        return self.expect()

    def close(self):
        """
        Close the active connection
        """
        self.client.close()
        self.logged_in = False

    def read_input(self):
        """
        Read from the client
        """
        self.last_client_usage = time.time()
        return self.client.read_until(
            b"\n", timeout=3
        ).decode("ascii")

    def expect(self):
        """
        Read from the client until it reads a line that matches
        one of the given expected strings (in regex form)
        """
        self.last_client_usage = time.time()
        return self.client.expect(
            [
                #                "\n",
                b"Out[0-9] In[0-9] All",  # Out1 In2 All
                b"In[0-9] All",  # In3 All
                b"^[0-9]+$",  # 4
                b"Tke",
                b"Login Administrator",
                b"Bytes Left"
            ], timeout=2
        )

    def send_cmd(self, cmd, needs_esc=True):
        """
        Sends a command to the Extron device
        """
        if needs_esc:
            cmd = "{}{}".format(self.ESC, cmd)
        self.client.write(cmd.encode("ascii") + b"\n")
        return self.expect()


def change_input_example():
    sw_4_2 = ExtronClient("192.168.1.100", password="example")
    sw_4_2.log_in()
    print(sw_4_2.change_input(2))


def save_and_download_image_example():
    mgp_641_xi = ExtronClient("192.168.1.101", password="example")
    mgp_641_xi.log_in()
    mgp_641_xi.capture_image()
    mgp_641_xi.save_image(delete=True)
    print("Image saved to", mgp_641_xi.image_filename)


def cec_power_on_example():
    in_1804 = ExtronClient("192.168.1.102", password="")
    in_1804.log_in()
    print(in_1804.cec_on())


def change_input_and_output_example():
    xtp_ii_32 = ExtronClient("192.168.1.103", password="")
    xtp_ii_32.log_in()
    print(xtp_ii_32.change_input(1, 2))  # display input 1 on output 2
