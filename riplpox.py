"""
RipL+POX.  As simple a data center controller as possible.
"""

from pox.core import core
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin

from ripl.mn import topos

from util import buildTopo, getRouting

log = core.getLogger()

# Number of bytes to send for packet_ins
MISS_SEND_LEN = 2000


# Borrowed from pox/forwarding/l2_multi
class Switch (EventMixin):
  def __init__ (self):
    self.connection = None
    self.ports = None
    self.dpid = None
    self._listeners = None

  def __repr__ (self):
    return dpidToStr(self.dpid)

  def disconnect (self):
    if self.connection is not None:
      log.debug("Disconnect %s" % (self.connection,))
      self.connection.removeListeners(self._listeners)
      self.connection = None
      self._listeners = None

  def connect (self, connection):
    if self.dpid is None:
      self.dpid = connection.dpid
    assert self.dpid == connection.dpid
    if self.ports is None:
      self.ports = connection.features.ports
    self.disconnect()
    log.debug("Connect %s" % (connection,))
    self.connection = connection
    self._listeners = self.listenTo(connection)

  def send_packet_data(self, outport, data = None):
    msg = of.ofp_packet_out(in_port=of.OFPP_NONE, data = data)
    msg.actions.append(of.ofp_action_output(port = outport))
    self.connection.send(msg)

  def send_packet_bufid(self, outport, buffer_id = -1):
    msg = of.ofp_packet_out(in_port=of.OFPP_NONE)
    msg.actions.append(of.ofp_action_output(port = outport))
    msg.buffer_id = buffer_id
    self.connection.send(msg)

  def install(self, port, match, buf = -1):
    msg = of.ofp_flow_mod()
    msg.match = match
    msg.idle_timeout = 10000
    msg.hard_timeout = 60000
    msg.actions.append(of.ofp_action_output(port = port))
    msg.buffer_id = buf
    self.connection.send(msg)

  def clear(self):
    msg = of.ofp_flow_mod()
    msg.command = 3
    self.connection.send(msg)


  def _handle_ConnectionDown (self, event):
    self.disconnect()
    pass


class DCellController(EventMixin):

  def __init__ (self):
    self.switches = {}  # Switches seen: [dpid] -> Switch
    self.macTable = {}  # [mac] -> (dpid, port)

    # TODO: generalize all_switches_up to a more general state machine.
    self.all_switches_up = False  # Sequences event handling.
    self.listenTo(core.openflow, priority=0)
    self.linkDown = False
    self.switchDown = False

  def _raw_dpids(self, arr):
    "Convert a list of name strings (from Topo object) to numbers."
    return [self.t.id_gen(name = a).dpid for a in arr]

  def _install_path(self, event, out_dpid, final_out_port, packet):
    "Install entries on route between two switches."
    in_name = 's' + str(event.dpid)
    out_name = 's' + str(out_dpid)
    route = self.r.get_route(in_name, out_name)
    log.info("route: %s" % route)
    match = of.ofp_match.from_packet(packet)
    for i, node in enumerate(route):
      node_dpid = self.t.id_gen(name = node).dpid
      if i < len(route) - 1:
        next_node = route[i + 1]
        out_port, next_in_port = self.t.port(node, next_node)
      else:
        out_port = final_out_port
      self.switches[node_dpid].install(out_port, match)

  def _handle_PacketIn(self, event):
    print "*****************PacketIn"
    #log.info("*************Parsing PacketIn.")
    if not self.all_switches_up:
      log.info("Saw PacketIn before all switches were up - ignoring.")
      return
    
    else:

      packet = event.parsed
      dpid = event.dpid
      in_port = event.port
      
      legal = False
      for i in range(1, 6):
        for j in range(1, 5):
            if str(packet.src) == '00:0'+str(i)+':0'+str(j)+':00:00:00':
              legal = True
      if not legal:
        log.info("Saw PacketIn from unknown MAC %s - ignoring." % packet.src)
        return
        
      
     
      
      
      log.info("Packet ID: %s" % packet)
      #log.info("Packet DST DCell: %s" % (str(packet)[23]))
      #log.info("Packet Src: %s" % packet.src)
      #log.info("Packet Dst: %s" % packet.dst)
      #log.info("DPID: %d" % dpid)
      #log.info("In Port: %d" % in_port)
      
      swCell = str(dpid)[0]
      swNode = str(dpid)[-1]
 
      #dstCell = packet.dst[4]
      #dstNode = packet.dst[7]
      

      if str(packet)[19] == 'f':
        dstCell = str(packet)[-3]
        dstNode = str(packet)[-1]
      else:
        dstCell = str(packet)[23]
        dstNode = str(packet)[26]
      

      

      if (not self.linkDown) and (not self.switchDown):
        if dpid > 10:
          if in_port == 1:
            if dstCell == swCell and dstNode == swNode:
              return
            elif dstCell == swCell:
              out_port = 2
            elif dstCell < swCell and dstCell == swNode:
              out_port = 3
            elif dstCell > swCell and dstCell == str(dpid + 1)[-1]:
              out_port = 3
            else:
              out_port = 2

          elif in_port == 2:
            if dstCell ==swCell and dstNode == swNode:
              out_port = 1
            else:
              out_port = 3

          elif in_port == 3:
            if dstCell ==swCell and dstNode == swNode:
              out_port = 1
            else:
              out_port = 2

        else:
          if dstCell == swCell:
            out_port = int(dstNode)
          elif dstCell > swCell:
            out_port = int(dstCell) - 1
          else:
            out_port = int(dstCell)

              

      else:

        if dpid > 10:
          if in_port == 1:
            if dstCell == swCell and dstNode == swNode:
              return
            elif dstCell == swCell:
              out_port = 2
            else:
              out_port = 3

          elif in_port == 2:
            if dstCell ==swCell and dstNode == swNode:
              out_port = 1
            else:
              out_port = 3

          elif in_port == 3:
            if dstCell ==swCell and dstNode == swNode:
              out_port = 1
            else:
              out_port = 2

        else:
          if dstCell == swCell:
            out_port = int(dstNode)
          elif dstCell > swCell:
            out_port = int(dstCell) - 1
          else:
            out_port = int(dstCell)


      match = of.ofp_match.from_packet(packet)    
      self.switches[dpid].install(out_port, match)                                                                       
      self.switches[dpid].send_packet_data(out_port, event.data)


    
      # Learn MAC address of the sender on every packet-in.
      #self.macTable[packet.src] = (dpid, in_port)#
  
      #log.info("mactable: %s" % self.macTable)
  
      # Insert flow, deliver packet directly to destination.
      #if packet.dst in self.macTable:#
        #out_dpid, out_port = self.macTable[packet.dst]#
        #self._install_path(event, out_dpid, out_port, packet)#

        #log.info("sending to entry in mactable: %s %s" % (out_dpid, out_port))
        #self.switches[out_dpid].send_packet_data(out_port, event.data)#

      #else:#
        # Broadcast to every output port except the input on the input switch.
        # Hub behavior, baby!
        #for sw in self._raw_dpids(t.layer_nodes(t.LAYER_EDGE)):#
          #log.info("considering sw %s" % sw)
          #ports = []#
          #sw_name = t.id_gen(dpid = sw).name_str()#
          #for host in t.down_nodes(sw_name):#
            #sw_port, host_port = t.port(sw_name, host)#
            #if sw != dpid or (sw == dpid and in_port != sw_port):#
              #ports.append(sw_port)#
          # Send packet out each non-input host port
          # TODO: send one packet only.
          #for port in ports:#
            #log.info("sending to port %s on switch %s" % (port, sw))
            #buffer_id = event.ofp.buffer_id
            #if sw == dpid:
            #  self.switches[sw].send_packet_bufid(port, event.ofp.buffer_id)
            #else:
            #self.switches[sw].send_packet_data(port, event.data)#
            #  buffer_id = -1


  def _handle_ConnectionUp (self, event):
    print "*****************ConnectionUp"
    sw = self.switches.get(event.dpid)
    sw_str = dpidToStr(event.dpid)
    log.info("Saw switch come up: %s", sw_str)
    found = False
    for i in range(1,6):
      if event.dpid == i:
        found = True
      for j in range(1,5):
        if event.dpid == (10 * i + j):
          found = True
    if not found :
      log.warn("Ignoring unknown switch %s" % sw_str)
      return
    if sw is None:
      log.info("Added fresh switch %s" % sw_str)
      sw = Switch()
      self.switches[event.dpid] = sw
      sw.connect(event.connection)
    else:
      log.info("Odd - already saw switch %s come up" % sw_str)
      sw.connect(event.connection)
    sw.connection.send(of.ofp_set_config(miss_send_len=MISS_SEND_LEN))

    if len(self.switches) == 25:
      log.info("Woo!  All switches up")
      self.all_switches_up = True


  def _clear_Switches (self):
    for i in range(1,6):
      self.switches[i].clear()
      for j in range(1,5):
        self.switches[10 * i + j].clear()

  def _handle_PortStatus (self, event):
    print "****************PortStatus"

    #print dir(event.ofp)
    #log.info("Packet DPID: %s" % event.dpid)
    #log.info("Packet PORT: %s" % event.port)
    #log.info("Packet OFP: %s" % event.ofp)
    #log.info("Packet REAS: %s" % event.ofp.reason)
    #log.info("Packet PACK: %s" % event.ofp.pack)
    #log.info("Packet SHOW: %s" % event.ofp.show)
    #log.info("Packet CONF: %s" % event.ofp.desc.config)
    #log.info("Packet STAT: %s" % event.ofp.desc.state)
    
    
    
    if event.ofp.desc.state == 1 and event.ofp.desc.config == 1:    
      log.info("Link Down: DPID = %s, PORT = %s" % (event.dpid, event.port))
      self.linkDown = True
      self._clear_Switches()
    elif event.ofp.desc.state == 0 and event.ofp.desc.config == 0:
      log.info("Link Up: DPID = %s, PORT = %s" % (event.dpid, event.port))
      self.linkDown = False


  def _handle_ConnectionDown (self, event):
    print "*****************ConnectionDown"
   
    log.info("Switch Down: DPID = %s" % event.dpid)
    self.switchDown = True
    self._clear_Switches()


def launch():
  """
  Args in format toponame,arg1,arg2,...
  """
  
  core.registerNew(DCellController)

  log.info("DCell running")
