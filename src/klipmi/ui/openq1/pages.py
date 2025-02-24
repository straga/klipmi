"""
Copyright 2024 Joe Maples <joe@maples.dev>

This file is part of klipmi.

klipmi is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

klipmi is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
klipmi. If not, see <https://www.gnu.org/licenses/>. 

"""



import asyncio

from PIL.Image import init
from nextion import EventType

from klipmi.model.ui import BasePage
from klipmi.utils import classproperty

import logging


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


async def check_component_vis(self, component_name: str) -> bool:
    try:
        # Try to get the visibility value of the component
        await self.state.display.get(f"{component_name}.vis")
        return True
    except:
        return False
    

class HeaterManager:
    HEATERS = {
        "extruder": {
            "name": "extruder",
            "title": "Extruder",
            "max_digits": 3
        },
        "bed": {
            "name": "heater_bed", 
            "title": "Bed",
            "max_digits": 2
        },
        "chamber": {
            "name": "chamber",
            "title": "Chamber",
            "max_digits": 2
        }
    }

    heater_data = None

    def __init__(self, printer):
        self.printer = printer

    def set_temperature(self, heater: str, temperature: int):
        self.printer.run_macro("SET_HEATER_TEMPERATURE", 
                             HEATER=heater, 
                             TARGET=temperature)
        self.heater_data = None


    def get_heater_config(self, heater_key: str) -> dict:
        heater = self.HEATERS[heater_key]
        return {
            "name": heater["name"],
            "title": heater["title"],
            "max_digits": heater["max_digits"],
            "callback": lambda t: self.set_temperature(heater["name"], t)
        }
    
    def set_heater_data(self, heater_key: str):
        self.heater_data = self.get_heater_config(heater_key)
        




class OpenQ1Page(BasePage):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self.state, 'heater_manager'):
            self.state.heater_manager = HeaterManager(self.state.printer)

    def handleNavBarButtons(self, component_id: int):
        if component_id == 30:
            self.changePage(MainPage)
        elif component_id == 31:
            self.changePage(MovePage)
        elif component_id == 32:
            self.changePage(FilelistPage)
        elif component_id == 33:
            self.changePage(SettingsPage)


class BootPage(BasePage):
    @classproperty
    def name(cls) -> str:
        return "logo"

    @classproperty
    def id(cls) -> int:
        return 0

    async def init(self):
        await self.state.display.set("version.val", 18, self.state.options.timeout)


class MainPage(OpenQ1Page):


    @classproperty
    def name(cls) -> str:
        return "main"

    @classproperty
    def id(cls) -> int:
        return 3

    # Element image id's
    _regular = 32
    _highlight = 33

    # Thumbnail
    filename = ""

    def isHeating(self, heaterData: dict) -> bool:
        return heaterData["target"] > heaterData["temperature"]

    async def setHighlight(self, element: str, highlight: bool):
        await self.state.display.set(
            "%s.picc" % element, self._highlight if highlight else self._regular
        )

    async def init(self):
        await self.state.display.set("b6.picc", 31)
        await self.state.display.set("tip.txt", "")      # Clear display field
        #Trun off logging DEBUG
        logging.getLogger().setLevel(logging.INFO)


    async def onDisplayEvent(self, type: EventType, data):
        log.info(f"Main: onDisplayEvent: EventType: {type}, data: {data}")
        if type == EventType.TOUCH:
            if data.component_id == 0:
                self.state.printer.togglePin("caselight")

                #temporary printing page
                #self.changePage(PrintingPage) 

            elif data.component_id == 1:
                self.state.printer.togglePin("sound")
                self.state.printer.togglePin("beep")
            elif data.component_id == 2:
                self.state.printer.emergencyStop()

            elif data.component_id == 21:  # extruder
                self.state.heater_manager.set_heater_data("extruder")
                self.state.return_page = self.__class__  # Store current page class
                self.changePage(KeypadPage)
                
            elif data.component_id == 22:  # Стоbed
                self.state.heater_manager.set_heater_data("bed")
                self.state.return_page = self.__class__  # Store current page class
                self.changePage(KeypadPage)
                
            elif data.component_id == 23:  # chamber
                self.state.heater_manager.set_heater_data("chamber")
                self.state.return_page = self.__class__  # Store current page class
                self.changePage(KeypadPage)

            else:
                self.handleNavBarButtons(data.component_id)


    async def onPrinterStatusUpdate(self, data: dict):

        #log.info(f"Main: onPrinterStatusUpdate: {data}")

        state = data["print_stats"]["state"]
        if state == "printing":
            self.changePage(PrintingPage)


        await self.state.display.set("n0.val", int(data["extruder"]["temperature"]))
        await self.setHighlight("b3", self.isHeating(data["extruder"]))

        await self.state.display.set("n1.val", int(data["heater_bed"]["temperature"]))
        await self.setHighlight("b4", self.isHeating(data["heater_bed"]))

        await self.state.display.set(
            "n2.val", int(data["heater_generic chamber"]["temperature"])
        )
        await self.setHighlight("b5", self.isHeating(data["heater_generic chamber"]))

        await self.setHighlight("b0", data["output_pin caselight"]["value"] > 0)
        await self.setHighlight("b1", data["output_pin sound"]["value"] > 0)



        filename = data["print_stats"]["filename"]
        await self.state.display.set("t0.txt", filename)

        if filename == "":
            await self.state.display.command("vis cp0,0")
        else:
            if filename != self.filename:
                self.filename = filename
                await self.uploadThumbnail("cp0", 160, "4d4d4d", self.filename)
                await self.state.display.command("vis cp0,1")


class PrintingPage2(OpenQ1Page):

    @classproperty
    def name(cls) -> str:
        return "printing2"

    @classproperty
    def id(cls) -> int:
        return 12
    
    # Element image id's
    _regular = 32
    _highlight = 33

    # Thumbnail
    filename = ""

    async def init(self):
        pass

    async def onDisplayEvent(self, type: EventType, data):
        log.info(f"PrintingPage2: onDisplayEvent: EventType: {type}, data: {data}")

        if type == EventType.TOUCH:
            if data.component_id == 0:
                self.changePage(PrintingPage)


# Printing page Main
class PrintingPage(OpenQ1Page):

    @classproperty
    def name(cls) -> str:
        return "printing"

    @classproperty
    def id(cls) -> int:
        return 8
    
    # Element image id's
    _regular = 51
    _highlight = 52

    # Thumbnail
    filename = ""

    def isHeating(self, heaterData: dict) -> bool:
        return heaterData["target"] > heaterData["temperature"]

    async def setHighlight(self, element: str, highlight: bool):
        await self.state.display.set(
            "%s.picc" % element, self._highlight if highlight else self._regular
        )


    async def init(self):
        await self.state.display.set("n4.val", 0) # Hotend fan # "heater_fan hotend_fan": ["speed"],      
        await self.state.display.set("n5.val", 0) # Part cooling  "fan_generic cooling_fan": ["speed"],        
        await self.state.display.set("n6.val", 0) # Chamber fan # "heater_fan chamber_fan": ["speed"],          

    
    def format_time(self, seconds: float) -> str:
        """Format seconds into HH:MM format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"


    async def onPrinterStatusUpdate(self, data: dict):

        log.info(f"Main: onPrinterStatusUpdate: {data}")

        state = data["print_stats"]["state"]

        if state != "printing":
            self.changePage(MainPage)

        
        # Extruder
        await self.state.display.set("n0.val", int(data["extruder"]["temperature"]))
        await self.setHighlight("b0", self.isHeating(data["extruder"]))
        extruder_target = int(data["extruder"]["target"])
        await self.state.display.set("t0.txt", f"{extruder_target}")


        # Bed
        await self.state.display.set("n1.val", int(data["heater_bed"]["temperature"]))
        await self.setHighlight("b1", self.isHeating(data["heater_bed"]))
        bed_target = int(data["heater_bed"]["target"])
        await self.state.display.set("t1.txt", f"{bed_target}")


        # Chamber
        await self.state.display.set("n2.val", int(data["heater_generic chamber"]["temperature"]))
        await self.setHighlight("b7", self.isHeating(data["heater_generic chamber"]))
        chamber_target = int(data["heater_generic chamber"]["target"])
        await self.state.display.set("t5.txt", f"{chamber_target}")


        # Caselight
        await self.setHighlight("b3", data["output_pin caselight"]["value"] < 1)


        # Fans handling with null checks
        def get_fan_speed(fan_data: dict) -> int:
            """Safely get fan speed as percentage"""
            if not fan_data or fan_data.get("speed") is None:
                return 0
            return int(fan_data["speed"] * 100)

        fan_speed_1 = get_fan_speed(data.get("fan_generic cooling_fan"))
        await self.state.display.set("n4.val", fan_speed_1)

        fan_speed_2 = get_fan_speed(data.get("fan_generic auxiliary_cooling_fan"))
        await self.state.display.set("n5.val", fan_speed_2)

        fan_speed_3 = get_fan_speed(data.get("heater_fan chamber_fan"))
        await self.state.display.set("n6.val", fan_speed_3)

        await self.setHighlight("b4", fan_speed_1 > 0)
        await self.setHighlight("b5", fan_speed_2 > 0)
        await self.setHighlight("b6", fan_speed_3 > 0)


        # Filename
        filename = data["print_stats"]["filename"]
        await self.state.display.set("t4.txt", filename)

        if filename == "":
             await self.state.display.command("vis cp0,0")
        else:
            if filename != self.filename:
                self.filename = filename
                await self.uploadThumbnail("cp0", 160, "4d4d4d", self.filename)
                await self.state.display.command("vis cp0,1")


        # Progress tracking
        progress = data["display_status"]["progress"] * 100
        print_duration = data["print_stats"]["print_duration"]
        total_duration = data["print_stats"]["total_duration"]
        
        # Progress bar and percentage
        await self.state.display.set("j0.val", int(progress))
        await self.state.display.set("n7.val", int(progress))
        
        # Time display
        if print_duration > 0:
            # Current time
            await self.state.display.set("t2.txt", self.format_time(print_duration))
            
            # Estimated total time
            if progress > 0:
                estimated_total = print_duration / (progress / 100)
                await self.state.display.set("t3.txt", self.format_time(estimated_total))
            else:
                await self.state.display.set("t3.txt", "--:--")
        else:
            # Clear time displays if not printing
            await self.state.display.set("t2.txt", "--:--")
            await self.state.display.set("t3.txt", "--:--")
    


    async def onDisplayEvent(self, type: EventType, data):
        log.info(f"Main: onDisplayEvent: EventType: {type}, data: {data}")

        if type == EventType.TOUCH:
            if data.component_id == 3:
                self.state.printer.togglePin("caselight")

            elif data.component_id == 10:
                self.state.printer.pausePrint()
                self.changePage(PausePage)
                #temporary back to home
                #self.changePage(MainPage)

            elif data.component_id == 11:
                self.state.printer.emergencyStop()

            elif data.component_id == 21:  # extruder
                self.state.heater_manager.set_heater_data("extruder")
                self.state.return_page = self.__class__  # Store current page class
                self.changePage(KeypadPage)
                
            elif data.component_id == 22:  # Стоbed
                self.state.heater_manager.set_heater_data("bed")
                self.state.return_page = self.__class__  # Store current page class
                self.changePage(KeypadPage)
                
            elif data.component_id == 23:  # chamber
                self.state.heater_manager.set_heater_data("chamber")
                self.state.return_page = self.__class__  # Store current page class
                self.changePage(KeypadPage)

            elif data.component_id == 2:
                self.changePage(PrintingPage2)

            else:
                self.handleNavBarButtons(data.component_id)


# KEyboard page
class KeypadPage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "keybdB"

    @classproperty
    def id(cls) -> int:
        return 9
    
    async def init(self):
        self.input_value = ""
        # Initialize display components

        await self.state.display.set("t2.txt", "") # start progress time
        await self.state.display.set("t3.txt", "") # end progress time
        await self.state.display.set("j0.val", 0) # progress bar
        await self.state.display.set("t4.txt", "") # progress time
        await self.state.display.set("n7.val", 0) # progress time
        await self.state.display.set("t100.txt", "") # name for what set temperature

        await self.state.display.set("inputlenth.val", 3)  # Max input length
        await self.state.display.set("show.txt", "")      # Clear display field

        # Show heater name from state
        if hasattr(self.state.heater_manager, 'heater_data'):
            heater_data = self.state.heater_manager.heater_data
            await self.state.display.set("t100.txt", heater_data["title"])
            await self.state.display.set("inputlenth.val", heater_data["max_digits"])

        if not hasattr(self.state, 'return_page'):
            self.state.return_page = MainPage

    async def onDisplayEvent(self, type: EventType, data):
        log.info(f"KeypadPage: onDisplayEvent: EventType: {type.name}, data: {data}")

        if type == EventType.TOUCH:
            comp_id = data.component_id
            if comp_id == 32:  # Back button
               self.changePage(self.state.return_page)
               self.state.return_page = None  # Clear return page

            elif comp_id == 31: # set temperature button
                value = await self.state.display.get("input.txt")
                temp = int(value)   
                log.info(f"Get temperature (int): {temp}")
                
                # Call callback function for set temperature
                heater_data = self.state.heater_manager.heater_data
                heater_data["callback"](temp)
                
                # Return to stored page
                self.changePage(self.state.return_page)
                self.state.return_page = None  # Clear return page



class MovePage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "move"

    @classproperty
    def id(cls) -> int:
        return 18

    async def onDisplayEvent(self, type: EventType, data):
        if type == EventType.TOUCH:
            if data.component_id == 22:
                self.changePage(FilamentPage)
            else:
                self.handleNavBarButtons(data.component_id)

    async def onPrinterStatusUpdate(self, data: dict):
        await self.state.display.set(
            "t0.txt", f'{data["motion_report"]["live_position"][0]:.1f}'
        )
        await self.state.display.set(
            "t1.txt", f'{data["motion_report"]["live_position"][1]:.1f}'
        )
        await self.state.display.set(
            "t2.txt", f'{data["motion_report"]["live_position"][2]:.1f}'
        )


class FilelistPage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "filelist"

    @classproperty
    def id(cls) -> int:
        return 4

    async def onDisplayEvent(self, type: EventType, data):
        if type == EventType.TOUCH:
            self.handleNavBarButtons(data.component_id)


class SettingsPage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "common_set"

    @classproperty
    def id(cls) -> int:
        return 45

    async def onDisplayEvent(self, type: EventType, data):
        if type == EventType.TOUCH:
            if data.component_id == 0:
                self.changePage(LanguagePage)
            if data.component_id == 22:
                self.changePage(CalibrationPage)
            else:
                self.handleNavBarButtons(data.component_id)


class LanguagePage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "language"

    @classproperty
    def id(cls) -> int:
        return 46

    async def onDisplayEvent(self, type: EventType, data):
        if type == EventType.TOUCH:
            if data.component_id == 0:
                self.changePage(SettingsPage)
            else:
                self.handleNavBarButtons(data.component_id)


class FilamentPage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "filament"

    @classproperty
    def id(cls) -> int:
        return 62

    # Element image id's
    _regular = 176
    _highlight = 177

    def isHeating(self, heaterData: dict) -> bool:
        return heaterData["target"] > heaterData["temperature"]

    async def setHighlight(self, element: str, highlight: bool):
        await self.state.display.set(
            "%s.picc" % element, self._highlight if highlight else self._regular
        )

    async def onDisplayEvent(self, type: EventType, data):
        if type == EventType.TOUCH:
            if data.component_id == 23:
                self.changePage(MovePage)
            else:
                self.handleNavBarButtons(data.component_id)

    async def onPrinterStatusUpdate(self, data: dict):
        await self.state.display.set(
            "t0.txt", str(int(data["extruder"]["temperature"]))
        )
        await self.state.display.set("n0.val", int(data["extruder"]["target"]))
        await self.setHighlight("b2", self.isHeating(data["extruder"]))
        await self.setHighlight("b0", self.isHeating(data["extruder"]))

        await self.state.display.set(
            "t1.txt", str(int(data["heater_bed"]["temperature"]))
        )
        await self.state.display.set("n1.val", int(data["heater_bed"]["target"]))
        await self.setHighlight("b3", self.isHeating(data["heater_bed"]))
        await self.setHighlight("b1", self.isHeating(data["heater_bed"]))

        await self.state.display.set(
            "t2.txt", str(int(data["heater_generic chamber"]["temperature"]))
        )
        await self.state.display.set(
            "n2.val", int(data["heater_generic chamber"]["target"])
        )
        await self.setHighlight("b12", self.isHeating(data["heater_generic chamber"]))
        await self.setHighlight("b13", self.isHeating(data["heater_generic chamber"]))


class CalibrationPage(OpenQ1Page):
    @classproperty
    def name(cls) -> str:
        return "level_mode"

    @classproperty
    def id(cls) -> int:
        return 27

    async def onDisplayEvent(self, type: EventType, data):
        if type == EventType.TOUCH:
            if data.component_id == 23:
                self.changePage(SettingsPage)
            else:
                self.handleNavBarButtons(data.component_id)

'''
0 - back
2 - restart klipper
3 - restart firmware
'''
class ResetPage(BasePage):
    @classproperty
    def name(cls) -> str:
        return "reset"

    @classproperty
    def id(cls) -> int:
        return 48
    
    async def onDisplayEvent(self, type: EventType, data):
        log.info(f"Reset: onDisplayEvent: EventType: {type.name}, data: {data}")

        if type == EventType.TOUCH:
            comp_id = data.component_id

            if comp_id == 0:
                self.changePage(MainPage)
            elif comp_id == 2:
                self.state.printer.restart()
            elif comp_id == 3:
                self.state.printer.firmwareRestart()
            else:  
                self.handleNavBarButtons(data.component_id)
    
