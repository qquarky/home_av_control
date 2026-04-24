"""
I needed a simple way to control my Anthem MRX 740 8K receiver which
existing solutions did not provide like "anthemav"
"""
import enum
import telnetlib
import time


class AnthemMessage(enum.Enum):
    """
    Anthem MRX 740 (8K) commands
    Note that Z1 stands for "Zone 1"
    Commands can be found at:
      https://anthemav.com/downloads/MRX-x40-AVM-70-90-IP-RS-232-v5.xls
    """
    CHECK_POWER = "Z1POW?;"
    POWER_ON = "Z1POW1;"
    POWER_OFF = "Z1POW0;"

    CHECK_VOL = "Z1VOL?;"
    SET_VOL_DB = "Z1VOL-{};"
    VOL_UP = "Z1VUP;"
    VOL_DN = "Z1VDN;"
    VOL_MUTE = "Z1MUTt;"

    SET_ANALOG_1 = "Z1INP13;"
    SET_STREAMING = "Z1INP9;"
    GET_INPUT = "Z1INP?;"


class AnthemMrx:
    TERMINATE = ";".encode()

    def __init__(self, host, port=14999):
        self.host = host
        self.port = port
        self.client = None
        self.last_client_usage = time.time()
        self.logged_in = False

    def log_in(self):
        """
        Log into the Anthem MRX receiver
        """
        if(
                time.time() - self.last_client_usage > 30
                or not self.logged_in
        ):
            if self.client is not None:
                self.client.close()
            self.client = telnetlib.Telnet(self.host, port=self.port)
            self.logged_in = True

    def update_time(self):
        """
        Update the last used time
        """
        self.last_client_usage = time.time()

    def get_response_from_message(self, message):
        """
        log in, if needed, send the message, and return its response
        """
        self.log_in()
        self.client.write(message.encode())
        response = self.client.read_until(self.TERMINATE, timeout=2)
        self.update_time()
        return response.decode()

    def is_powered_on(self):
        """
        Check if the receiver is powered on
        """
        response = self.get_response_from_message(
            AnthemMessage.CHECK_POWER.value
        )
        if response:
            return response.endswith("POW1;")
        return False

    def get_volume(self):
        """
        Get the current volume level)
        :return:
        """
        response = self.get_response_from_message(
            AnthemMessage.CHECK_VOL.value
        )
        return response.strip(";").split("VOL")[-1]

    def power_on(self):
        """
        Turn on the receiver
        """
        return self.get_response_from_message(
            AnthemMessage.POWER_ON.value
        )

    def set_volume(self, num):
        """
        Set the volume to the given number, in dB
        """
        return self.get_response_from_message(
            AnthemMessage.SET_VOL_DB.value.format(num)
        )

    def volume_up(self):
        """
        Increase the volume by 0.5 dB
        """
        return self.get_response_from_message(
            AnthemMessage.VOL_UP.value
        )

    def volume_down(self):
        """
        Decrease the volume by 0.5 dB
        """
        return self.get_response_from_message(
            AnthemMessage.VOL_DN.value
        )

    def volume_mute(self):
        """
        Mute the volume--can be undone by running again or
        increasing/decreasing/setting the volume
        """
        return self.get_response_from_message(
            AnthemMessage.VOL_MUTE.value
        )

    def set_analog_output(self):
        """
        Set the receiver to use analog 1
        """
        return self.get_response_from_message(
            AnthemMessage.SET_ANALOG_1.value
        )

    def set_streaming_output(self):
        """
        Set the receiver to use streaming
        """
        return self.get_response_from_message(
            AnthemMessage.SET_STREAMING.value
        )


def change_input_to_analog_1_example():
    mrx_740 = AnthemMrx("191.168.1.100", 14999)
    if not mrx_740.is_powered_on():
        mrx_740.power_on()
    mrx_740.set_analog_output()


def volume_up_example():
    mrx_740 = AnthemMrx("191.168.1.100", 14999)
    if not mrx_740.is_powered_on():
        mrx_740.power_on()
    mrx_740.volume_up()
