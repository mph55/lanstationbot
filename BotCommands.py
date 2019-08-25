import discord
import asyncio
import struct
import ast
import urllib.parse
import config

def format_packet(msg):
    return b"\x00\x83" + struct.pack(">H", len(msg) + 6) + \
    b"\x00\x00\x00\x00\x00" + bytes(msg, "ascii") + b"\x00"

def handle_outgoing(payload, loop):

    reader, writer = yield from asyncio.open_connection(config.host, config.gameport, loop=loop)
    packet = format_packet(payload)

    writer.write(packet)

    headerReceived = yield from reader.read(2)
    if headerReceived != b"\x00\x83":
        print("Unexpected packet.")

    packetLength = yield from reader.read(2)
    packetLength = int.from_bytes(packetLength, "big")
    received = yield from reader.read(packetLength)
    received = received[1:-1]
    received = received.decode("utf8")

    writer.close()
    return received

def get_command(messageObj):

    commandstring = ""
    parameter = ""
    cmdMsg = ""

    i = messageObj.content.strip(config.triggerString)
    commandstring = i.split(" ")[0]
    if len(i.split(" ")) >= 2:
        parameter = i.split(" ")[1]
        if len(i.split(" ", maxsplit=2)) >= 3:
            cmdMsg = i.split(" ", maxsplit=2)[2]
    command = (commandstring, parameter, cmdMsg)
    return command

def has_perms(user):
    for i in user.roles:
        if str(i) in config.perm_roles:
            return True
        else:
            perm = False
    return perm

class Command(object):

    def __init__(self, client, loop, message):
        self.client = client
        self.loop = loop
        self.message = message

    @asyncio.coroutine
    def do_command(self):
        pass

class Ping(Command):

    @asyncio.coroutine
    def do_command(self):
        try:
            command = get_command(self.message)[0]
            yield from handle_outgoing(command, self.loop)
            yield from self.message.channel.send("Server is online.")
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class Status(Command):

    @asyncio.coroutine
    def do_command(self):
        try:
            command = "status"
            status = yield from handle_outgoing(command, self.loop)
            status = urllib.parse.parse_qs(status)
            version = status["version"][0]
            admins = status["admins"][0]
            playercount = status["players"][0]
            gamemode = status["mode"][0]
            playerList = []
            for key in status:
                if "player" in key and not "players" in key:
                    playerList.append(status[key][0])
            statusMsg += "Station time: %s\r\n" % stationtime
            statusMsg += "Online players: %s\r\n```" % playercount
			statusMsg += "Gamemode: %s\r\n" % gamemode
            yield from self.message.channel.send(statusMsg)
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class Info(Command):

    def parse_damage(self, damage):
        dam = urllib.parse.parse_qs(damage)
        if dam == {}:
            damtup = ("Not living", "Not living", "Not living", "Not living", "Not living", "Not living")
        else:
            damtup = (dam["oxy"][0], dam["tox"][0], dam["fire"][0], dam["brute"][0], dam["clone"][0], dam["brain"][0])
        return damtup

    @asyncio.coroutine
    def do_command(self):
        try:
            commandtup = get_command(self.message)
            command = "?info=" + commandtup[1]
            command += ";key=" + config.commskey
            info = yield from handle_outgoing(command, self.loop)
            if info == "No matches":
                yield from self.message.channel.send("No matches.")
            else:
                info = urllib.parse.parse_qs(info)
                area = info["area"][0]
                info["area"][0] = area.replace("%ff", "")
                infoMsg = "```"
                infoMsg += "Key:           " + info["key"][0] + "\r\n"
                infoMsg += "Name:          " + info["name"][0] + "\r\n"
                infoMsg += "Species:       " + info["species"][0] + "\r\n"
                infoMsg += "Gender:        " + info["gender"][0] + "\r\n"
                infoMsg += "Role:          " + info["role"][0] + "\r\n"
                infoMsg += "Location:      " + info["loc"][0] + "\r\n"
                infoMsg += "Turf:          " + info["turf"][0] + "\r\n"
                infoMsg += "Area:          " + info["area"][0] + "\r\n"
                infoMsg += "Antag:         " + info["antag"][0] + "\r\n"
                infoMsg += "Has been rev?: "  
                if int(info["hasbeenrev"][0]):
                    infoMsg += "Yes" + "\r\n"
                else:
                    infoMsg += "No" + "\r\n"
                infoMsg += "Mob type:      " + info["type"][0] + "\r\n"
                damages = self.parse_damage(info["damage"][0])
                infoMsg += "Damage:        " + "\r\n"
                infoMsg += "--Oxy:   " + damages[0] + "\r\n"
                infoMsg += "--Tox:   " + damages[1] + "\r\n"
                infoMsg += "--Fire:  " + damages[2] + "\r\n"
                infoMsg += "--Brute: " + damages[3] + "\r\n"
                infoMsg += "--Clone: " + damages[4] + "\r\n"
                infoMsg += "--Brain: " + damages[5]
                infoMsg += "```"
                yield from self.message.channel.send(infoMsg)
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class AdminMsg(Command):

    @asyncio.coroutine
    def do_command(self):
        try:
            commandtup = get_command(self.message)
            author = self.message.author
            command = "?adminmsg=" + commandtup[1]
            command += ";msg=" + commandtup[2]
            command += ";key=" + config.commskey
            command += ";sender=" + author.name
            confirmation = yield from handle_outgoing(command, self.loop)
            yield from self.message.channel.send(confirmation)            
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class Notes(Command):

    def parse(self, qs):
        qs = qs.replace("%26%2334%3b", '"')
        qs = qs.replace("%26%2339%3b", '"')
        qs = qs.replace("%26amp%3b", "&")
        qs = qs.replace("%26%2339;", "'")
        qs = qs.replace("%0d", "\r")
        qs = qs.replace("%0a", "\n")
        qs = qs.replace("%28", "(")
        qs = qs.replace("%29", ")")
        qs = qs.replace("%2b", "+")
        qs = qs.replace("%2c", ",")
        qs = qs.replace("%2f", "/")
        qs = qs.replace("%3a", ":")
        qs = qs.replace("%3b", ";")
        qs = qs.replace("%3f", "?")
        qs = qs.replace("%5b", "[")
        qs = qs.replace("%5d", "]")
        qs = qs.replace("+", " ")
        return qs

    def format_for_sending(self, message):
        message = "```" + message + "```"
        return message

    @asyncio.coroutine
    def send(self, qs):
        message = self.parse(qs)
        if len(message) >= 1994:
            fmtmessage = self.format_for_sending(message[:1994])
            yield from self.message.channel.send(fmtmessage)
            message = message[1994:]
            yield from self.send(message)
        else:
            message = "```" + message + "```"
            yield from self.message.channel.send(message)

    @asyncio.coroutine
    def do_command(self):
        try:
            commandtup = get_command(self.message)
            command = "?notes=" + commandtup[1]
            command += ";key=" + config.commskey
            qs = yield from handle_outgoing(command, self.loop)
            yield from self.send(qs)
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class Age(Command):

    @asyncio.coroutine
    def do_command(self):
        try:
            commandtup = get_command(self.message)
            command = "?age=" + commandtup[1]
            command += ";key=" + config.commskey
            age = yield from handle_outgoing(command, self.loop)
            if age == "Ckey not found":
                yield from self.message.channel.send(age)
            else:
                yield from self.message.channel.send("Account is %s days old." % age)
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class IP(Command):

    @asyncio.coroutine
    def do_command(self):
        try:
            commandtup = get_command(self.message)
            command = "?ip=" + commandtup[1]
            command += ";key=" + config.commskey
            ip = yield from handle_outgoing(command, self.loop)
            yield from self.message.channel.send(ip)            
        except OSError:
            yield from self.message.channel.send("Server is offline.")

class Help(Command):

    @asyncio.coroutine
    def do_command(self):

        prepend = config.triggerString

        helpMsg = ""
        helpMsg += "```COMANDOS DO BOT DA LANSTATION:\r\n"
        helpMsg += prepend + "ping                 - checks if server is up\r\n"
        helpMsg += prepend + "status               - status, including round duration, station time,\r\n"
        if self.message.channel.id == config.ahelpID:
            helpMsg += prepend + "info <ckey>          - shows detailed information about ckey\r\n"
            helpMsg += prepend + "msg <ckey> <message> - adminhelps from discord to game\r\n"
            helpMsg += prepend + "notes <ckey>         - get player notes of ckey\r\n"
            helpMsg += prepend + "age <ckey>           - shows player age of ckey\r\n"
            helpMsg += prepend + "ip <ckey>            - shows IP of ckey"
        helpMsg += "```"
        yield from self.message.channel.send(helpMsg)