import os
import sys
import random
from migen import *
from migen.genlib.io import CRG

from migen.fhdl import verilog
from tx import TX
from migen.genlib.fifo import AsyncFIFO

class FullModeSim(Module):
    def __init__(self, platform):
       
        self.data=Signal(32) #data to fifo
        self.data_type=Signal(2) #data  type to fifo
        self.link_ready=Signal()
        self.fifo_we=Signal()
        self.fifo_full=Signal()
        
        self.reset=Signal()
        
        self.tx_clk=Signal() #clock from gtp (txusrclk2)
        self.write_clk=Signal() #clock for fifo
        
        self.txinit_done=Signal() #gtp tx init done
        self.tx_data=Signal(32) #data to gtp
     
   
        self.tx_k=Signal() #first byte special character for gtp 8b/10b encoder
        

        tx=TX()
        tx=ClockDomainsRenamer("tx")(tx)
       

        self.clock_domains.cd_write = ClockDomain()
        self.comb+=self.cd_write.clk.eq(self.write_clk)

        # tx clocking
        self.clock_domains.cd_tx = ClockDomain()
        self.comb+=[
            self.cd_tx.rst.eq(self.reset),
            self.cd_tx.clk.eq(self.tx_clk)
        ]        
    
        fifo=AsyncFIFO(width=34,depth=32768)
        fifo=ClockDomainsRenamer({"read":"tx"})(fifo)
        self.submodules+=[fifo,tx]
        self.comb+=[
            fifo.din.eq(Cat(self.data,self.data_type)),
            fifo.we.eq(self.fifo_we),
        ]
        self.comb+=[
            fifo.re.eq(tx.fifo_re),
            tx.link_ready.eq(self.link_ready),
            tx.fifo_empty.eq(~fifo.readable),
            self.fifo_full.eq(~fifo.writable),
            tx.tx_init_done.eq(self.txinit_done),
            If((self.link_ready & fifo.readable), 
                tx.data_type_in.eq(fifo.dout[32:]),
                tx.data_in.eq(fifo.dout[:32]), 
            ),
            self.tx_k.eq(tx.k),
            self.tx_data.eq(tx.data_out),
            
        ]

def generate_top():
    platform = Platform()
    soc = FullModeSim(platform)
    platform.build(soc, build_dir="./", run=False)
    #platform.build(soc)
    

def generate_top_tb():
    f = open("top_tb.v", "w")
    f.write("""
`timescale 1ns/1ps

module top_tb();

reg gtp_clk;
initial gtp_clk = 1'b1;
always #2.08333 gtp_clk = ~gtp_clk; //2.08333 is half period of 240 MHz gtp clk

reg sys_clk;
initial sys_clk = 1'b1;
always #2.5 sys_clk = ~sys_clk; //2.5 is half period of 200 MHz sys clk

real period =3.333; //400 MHz period

reg link_ready;
initial link_ready=0;
reg we;

reg reset;
initial reset='b0;
initial we='b0;

reg trans_en;
initial trans_en=0;

wire gtp_p;
wire gtp_n;
wire rxinitdone;
wire serial_tx;

top dut (
    .smatx_p(gtp_p),
    .smatx_n(gtp_n),
    .smarx_p(gtp_p),
    .smarx_n(gtp_n),
    .gtp_refclk_p(gtp_clk),
    .gtp_refclk_n(~gtp_clk),
    .sw2_0(link_ready),
    .sw2_1(we),
    .sw2_2(trans_en),
    .cpu_reset(reset),
    .rxinitdone(rxinitdone),
    .clk200_p(sys_clk),
    .clk200_n(~sys_clk),
    .serial_tx(serial_tx)
    
);


always begin 
    //Waits signals initialization
    for (integer i=0;i<=4000;i=i+1) begin
        #period;
    end
    
    while(~rxinitdone) begin
        #period;
    end
    
    for (integer i=0;i<=15000;i=i+1) begin
        #period;
    end
    

    //Starts transmision. It will send IDLE because FIFO is empty yet
    link_ready=1'b1; 
    for (integer i=0;i<=15000;i=i+1) begin
        #period;
    end
    
    //The writing process starts
    we=1'b1;


    for (integer i=0;i<=15000;i=i+1) begin
        #period;
    end

    trans_en=1'b1;
    
    while(1) begin
        #period;
    end

    we=1'b0;
    #period;
    we=1'b1;
    //The writing process starts again
    for (integer i=0;i<=35000;i=i+1) begin
        #period;
    end

    
end
endmodule""")
    f.close()

"""    
dut = FullModeSim(platform=0)   
verilog.convert(dut, {dut.link_ready,dut.reset, 
    dut.tx_data,dut.txinit_done, dut.write_clk, dut.tx_clk,
    dut.rx_data, dut.rxinit_done, dut.trans_en, dut.uart_tx,
    dut.rx_clk, dut.rxbytealigned, dut.rx_k, dut.tx_k, dut.led0,
    dut.led1, dut.led2, dut.led3, dut.we}).write("top_logic.v")
"""
dut = FullModeSim(platform=0)   
verilog.convert(dut, {dut.link_ready,dut.reset, dut.tx_data,
    dut.txinit_done, dut.write_clk, dut.tx_clk, dut.tx_k, 
    dut.data, dut.data_type, dut.fifo_we, dut.fifo_full}).write("top_full_mode_daphne.v")
