// TODO:
// reset checks
// oorst checks 
// psi checks
// exceptions
// du signals (seperate loop)
// internal rdr
// rtcc
// power up pu seq
// power down pu seq
// not writing to regs/signals when not expected
// compare ret signals to backdoor read 





`ifdef MSS_POS
   `error 
`else
   `define MSS_POS 0
`endif

`ifdef ISP_POS
   `error 
`else
   `define ISP_POS 1
`endif

`ifdef CLB_POS
   `error 
`else
   `define CLB_POS 2
`endif

// enum for selecting memory
typedef enum {RRT, NET} hws_mem_enum;
typedef enum {INTERNAL, EXTERNAL} hws_rdr_type_e;
typedef enum {FIRST_BOOT, NET_FETCH, RRT_FETCH, BRANCH} hws_ret_state_e;
typedef enum {FLL_RDR, PGX_RDR, FMU_RDR, SEC_RDR, CPU_ROM_RDR, SPU_ROM_RDR, CPU_NVM_RDR, SPU_NVM_RDR} hws_external_rdr_type_e;

// ============================================
//            SIGNAL_WATCHDOG
// ==========================================;=
// Macro to set an error if condition is false after ## soc_clk cycles 
// it uses wait_with_error function to print the error
// COND - @ vif.signal
// CYCLES - num of soc clock cycles
// TEXT - uniq string to set the error message (GO/DONE can add more in wait_with_error function
`define SIGNAL_WATCHDOG(COND, CYCLES, TEXT) begin \
   `BEGIN_FIRST_OF \
      COND; \
      wait_with_error(CYCLES, TEXT); \
   `END_FIRST_OF \
end

// ============================================
//            REG_WRITE_CHECK
// ============================================
// Macro to verify HW_write and check the data value
// I used #1ns to wait for correct value 
//
// SIGNAL_NAME - without vif. and without _wen or _wdata)
// REG_NAME - field name from optidoc
// VAL - expected value
//
// 1. wait for _wen with watchdoog
// 2. check _wdata
// 3. compare backdoor read
//
// TODO YS: add ret (or other) protocol checks
`define REG_WRITE_CHECK(SIGNAL_NAME, REG_NAME, VAL) begin \
   `uvm_info (get_type_name(),$sformatf("start <%0d> %s checks (0x%0h)",enter_calls, "``REG_NAME``", VAL), verbosity) \
   enter_calls ++; \
   `BEGIN_FIRST_OF \
      begin \
         wen_counter["``SIGNAL_NAME``"]++; \
         @(posedge vif.``SIGNAL_NAME``_wen); \
         #1ns if (vif.``SIGNAL_NAME``_wdata !== VAL) `uvm_error(get_type_name(),$sformatf("Signal %s value <0x%0h> is not <0x%0h>", "vif.``SIGNAL_NAME``_wdata", vif.``SIGNAL_NAME``_wdata, VAL)) \
      end \
      begin \
         repeat (6) @(posedge vif.soc_clk); \
         `uvm_error(get_type_name(), $sformatf({"``SIGNAL_NAME``"," was not written"})) \
      end \
   `END_FIRST_OF \
   #0; \
   fork \
      begin \
         /* wen is sampled on negedge */ \
         @(negedge vif.soc_clk); \
         /* task to wait according to ral */ \
          macro_delay("``REG_NAME``"); \
         #1ns if (field_backdoor_read("``REG_NAME``") !== VAL) `uvm_error(get_type_name(), $sformatf("Backdoor read value of field %s <0x%0h> is not <0x%0h>", "``REG_NAME``", field_backdoor_read("``REG_NAME``"), VAL)); \
      end \
   join_none\
   #0; \
   `uvm_info (get_type_name(),$sformatf("exit <%0d> %s checks (0x%0h)",exit_calls, "``REG_NAME``", VAL), verbosity) \
   exit_calls++; \
end

// ============================================
//            REG_WRITE_CHECK_START
// ============================================
// Macro to make REG_WRITE_CHECK run in a new thread
`define REG_WRITE_CHECK_START(SIGNAL_NAME, REG_NAME, VAL) begin \
   fork \
      begin \
         `REG_WRITE_CHECK(SIGNAL_NAME, REG_NAME, VAL); \
      end \
   join_none \
end \


class pixie_hws_sb extends uvm_scoreboard;
   `uvm_component_utils(pixie_hws_sb)
   int enter_calls = 0;
   int exit_calls = 0;   

   pixie_mailbox mailbox;
   pixie_hws_cfg cfg;
   virtual pixie_hws_if vif;

   uvm_verbosity verbosity = 1 ? UVM_LOW : UVM_DEBUG;
   uvm_status_e status; // for reading from memories
   uvm_reg hrr_registers[$]; // for accessing all block reg
   uvm_reg register; // for accessing all block reg
   uvm_reg_field reg_fields[$];   

   bit [31:0] temp_val = 32'hcafecafe; // for reading registers 
         
   string pu_name;
   string internal_name;
   string prefix = "Executing external RDR of type:"; // for printing
   string err_msg;
   int go_timout = 100; // TODO YS - set value soc_clk cycles before go
   int done_timout = 1000000; // TODO YS - soc_clk cycles before done
   
   // Sampeling pgen change by FW 
   bit isppd_at_go;
   bit isppd_at_done;
   bit msspd_at_go;
   bit msspd_at_done;

   pixie_mem nvm; // NVM memory model
   bit [31:0] net_offset; // start of net 
   
   pixie_mem rom; // ROM memory model
   bit [31:0] rrt_offset; // start of rrt
   
   pixie_mem dbg_ram; // debug ram memory model

   hws_mem_enum net_rrt_sel; // Current memory to fetch from
   int net_rd_index; // address in NVM (of 16 bit word)
   int rrt_rd_index; // address in ROM (of 16 bit word)
   
   int rrt_rd_cntr = 'h00; 
   bit rrt_rd_cntr_done = 1'b0; // indicates rrt_rd_cntr == 0
   
   
   hws_ret_state_e hws_ret_state; // TODO YS: not yet implemented - for branching
   
   hws_rdr_type_e rdr_type; // INTERNAL/EXTARNAL
   hws_external_rdr_type_e external_rdr_type; // Power unit FLL/PGX/SEC etc... 
   
   
   // power gate enable (1-on, 0-off) 
   bit clbpd = 0;
   bit msspd = 0;
   bit isppd = 0;
   
   bit [2:0] du_pgen = 3'b000;
   bit [2:0] du_rst = 3'b000;
 
   // previous power gate enable (1-on, 0-off) 
   bit clbpd_prev = 0;
   bit msspd_prev = 0;
   bit isppd_prev = 0;

   // ower gate enable on out of halt (1-on, 0-off) 
   bit clbpd_ooh = 0;
   bit msspd_ooh = 0;
   bit isppd_ooh = 0;

   bit dupd = 0; // TODO YS


   bit [15:0] exception_rdr; // built by detect_exception() task in case of exception
   bit exception_flag = 0; // Indicates exception occurre
   bit start_of_active_flag = 0; // Indicates HWS just got out of reset (used for exception detection)

   // rdr variables 
   // ============================================

   bit [15:0] rdr; // fetched from memories   
   
   bit b2bm;
   
   // EOL
   bit [7:0] nri; // NET RDR Index
   
   // GIC
   bit [3:0] cfr; // Clock frequency Control
   bit [3:0] vgr; // Vstart Gear - TBD
      
   // RPDC   
   bit [7:0] rrt_counter;
   
   // RPDI
   bit [8:0]rri; // RRD RDR Index
   
   // NOP
   
   // RTCC
   bit frc_reset;
   bit [2:0] timer_mode;
   bit [1:0] timer_index;
   bit [1:0] wake_up_mode;
   bit pend_vstart            = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
   bit vstart_count_timer_enb = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
   bit def_timer_enb          = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
   bit timer_except_en        = 1'b0; // implicit - not part of rtcc TODO YS: add logic for correct value
   bit pace_enb               = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
   bit [7:0] preset           = 1'b0; // implicit - not part of rtcc TODO YS: add logic for correct value
   bit [7:0] preset_s;        // sampling preset in order to solve race

   // External
   bit [1:0] psi;
   bit bpdo; // B2B Power Domains Off (SW PDs)
   bit sw_bpdo; // flag it was set by sw
   bit [8:0] pu_cmd;
   bit [12:0] cpu_rom_pc;
   bit [13:0] cpu_rom_cmd; // Command is padded to 14 bit (for rom bit 13 is 1)
   bit [12:0] spu_rom_index;
   bit [13:0] spu_rom_cmd; // Command is padded to 14 bit (for rom bit 13 is 1)
   bit [11:0] cpu_nvm_pc;
   bit [13:0] cpu_nvm_cmd; // Command is padded to 14 bit (for rom bit 13 is 1)
   bit [11:0] spu_nvm_index;
   bit [13:0] spu_nvm_cmd; // Command is padded to 14 bit (for rom bit 13 is 1)
   
   
   // DU
   bit just_got_out_of_halt = 0;   
   
   // Array to count numbers of writes to ret
   // on simulation end we check no more writes were done 
   int wen_counter [string];
   
   bit timer_was_set_during_current_wave = 1'b0; // flat // TODO: YS: maybe also for SW timer not only RTCC
   bit check_timer = 1'b0; // flag to check timer values if timer was set on prvious wave

   bit during_fetch_from_net = 1'b0; // indicates fetch is active
   bit during_fetch_from_rrt = 1'b0; // indicates fetch is active
   bit during_fetch_from_net_dbg_ram = 1'b0; // indicates fetch is active
   bit during_fetch_from_rrt_dbg_ram = 1'b0; // indicates fetch is active

   int expected_soft_awdt_counter_val = 0;
   int expected_hard_awdt_counter_val = 0;
   bit hard_awdt = 1'b0;

   bit init_done;

   int ret_cycles; // num of rtc_cycles during retention
   int curr_hrr_sys_time;
   int prev_hrr_sys_time;

   int hws_reset_while_halt = 0; // as name says - indicates if need to update sys time
   // ============================================
   //          run_between_brownouts()
   // ============================================  
   // Currently this is all what hws is doing 
   // If future can add brownouts support in run()
   task run_between_brownouts();
 
     
      // reset values
      net_rrt_sel = NET; // first fetch from NVM
      hws_ret_state = FIRST_BOOT;
      net_rd_index = 0; // address in NVM (of 16 bit word) - 0 is  addr for first fetch 
      rrt_rd_index = 0; // address in ROM (of 16 bit word) 
        
                        
      // Any iteration of this loop is a single "active" session
      forever
      begin

         timer_was_set_during_current_wave = 0;

         // Waiting for "out of reset" (active mode) 
         @(posedge vif.adb_hws_rstn iff vif.adb_hws_rstn === 1'b1);
         start_of_active_flag = 1'b1;
         du_pgen = 3'b000; // rgu is cleared on reset
         du_rst = 3'b000; // rgu is cleared on reset

         `uvm_info (get_type_name(),$sformatf("----------------------------- HWS Out Of Reset -----------------------------"), UVM_MEDIUM);
         if (cfg.power_mon_en)
         fork
               measure_soc_clock();
         join_none
         fork 
            soft_awdt_rm();
            hard_awdt_rm();
            pwrctl_rm();
            rstctl_rm();
            init_rm();
            begin if (cfg.sys_time_checker_en == 1'b1) sys_time_checker(); end
         join_none

         // Backdoor read of HRR registers to update mirrored value 
         // Setting all regs to zero by "The Machine" mess up the mirror value
         read_hrr_regs();
     
         //`uvm_info (get_type_name(),$sformatf("kakiwen_counter:"),verbosity);
         //foreach (wen_counter[key]) `uvm_info (get_type_name(),$sformatf("kakiwen_counter[%s] = %d", key, wen_counter[key]),verbosity);
         //`uvm_info (get_type_name(),$sformatf("kakiwen_counter:"),verbosity);


         // Single RDR or B2B RDRs(if not B2B -> break)
         do
         begin

            fork // protection fork
            begin
               // Halt or RDR fork
               fork 
                  begin

                     // If halt -> wait for "go" or  "no halt"
                     `uvm_info (get_type_name(),$sformatf("checking halt = 0x%0h", vif.du_hws_halt), verbosity);

                     if (vif.du_hws_halt === 1'b1)
                     begin
                        `BEGIN_FIRST_OF

                           forever
                           begin
                              `uvm_info (get_type_name(),$sformatf("sys_time: hws_reset_while_halt = %d", hws_reset_while_halt), verbosity);

                              @(negedge vif.adb_hws_rstn);
                              if (vif.du_hws_halt === 1'b1) hws_reset_while_halt++;
                              `uvm_info (get_type_name(),$sformatf("sys_time: hws_reset_while_halt = %d", hws_reset_while_halt), verbosity);
                           end

 
                           begin
                              @(posedge vif.du_hws_exe_go iff (vif.du_hws_exe_go === 1'b1), negedge vif.du_hws_halt iff (vif.du_hws_halt === 1'b0) );
                              `uvm_info (get_type_name(),$sformatf("*** Continue from halt ***"), verbosity);
                              // update sys_time(hws not writing while in halt)
                              if (vif.adb_hws_rstn === 1'b1 && hws_reset_while_halt > 0) //TODO what if adb_hws_rstn = 0??
                              begin
                                 prev_hrr_sys_time = vif.adb_hws_frc_counter; // TODO if halt is not on the start, need to add hrr value
                                 `uvm_info (get_type_name(),$sformatf("updating prev_hrr_sys_time on out of halt = %0d", prev_hrr_sys_time), verbosity);
                              end    
                              hws_reset_while_halt = 0;
                              `uvm_info (get_type_name(),$sformatf("sys_time: hws_reset_while_halt = %d", hws_reset_while_halt), verbosity);

                              // Sample PDs configuration set by DU while in halt
                              // YS: we need this in order not to turn these domains on
                              ///msspd_prev = vif.hws_adb_mss_pgen;      
                              ///isppd_prev = vif.hws_adb_isp_pgen;      
                              ///clbpd_prev = vif.hws_adb_clb_pgen;  
                              msspd_ooh = vif.hws_adb_mss_pgen;      
                              isppd_ooh = vif.hws_adb_isp_pgen;      
                              clbpd_ooh = vif.hws_adb_clb_pgen;

                               
                              msspd_prev = 0; isppd_prev = 0; clbpd_prev = 0;

                              just_got_out_of_halt = 1;
   

                              check_branch(); // if branch dirty bit was written during halt

                           end

                           begin
                              @(posedge vif.cif_hws_mss_cmd_go iff (vif.cif_hws_mss_cmd_go === 1'b1), 
                                posedge vif.cif_hws_spu_cmd_go iff (vif.cif_hws_spu_cmd_go === 1'b1), 
                                posedge vif.cif_hws_pgx_cmd_go iff (vif.cif_hws_pgx_cmd_go === 1'b1), 
                                posedge vif.cif_hws_fll_cmd_go iff (vif.cif_hws_fll_cmd_go === 1'b1), 
                                posedge vif.cif_hws_fmu_cmd_go iff (vif.cif_hws_fmu_cmd_go === 1'b1), 
                                posedge vif.cif_hws_sec_cmd_go iff (vif.cif_hws_sec_cmd_go === 1'b1))
                              `uvm_error(get_type_name(),$sformatf("HWS issued GO while in halt"))
                           end
                        `END_FIRST_OF
                     end

                     // Set prest to zero
                     set_preset(0, `__LINE__);


                     // Wait for hrr init done
                     // Before init done, signals from hrr to hws are 0 but backdoor read is 1
                     if (just_got_out_of_halt == 1)
                     begin
                        `uvm_info (get_type_name(),$sformatf("Wait for init not done = 0"), verbosity);
                        wait (vif.drr1_shadow_hrr_init_not_done === 1'b0);
                        `uvm_info (get_type_name(),$sformatf("After wait for init not done = 0"), verbosity);
                     end

                     // Check if exception occurred during retention
                     detect_exception();

                     if (check_timer == 1'b1) 
                     begin
                        // .start()
                        fork
                           begin 
                              repeat(2) @(posedge vif.soc_clk); // wait to shadow update from drr (clk_sel is from drr)
                              #1ns;  // cells delay from rgu
                              aon_timer_checker();
                              check_timer = 1'b0; // check only on first RDR (timer value can be changed by SW)
                           end
                        join_none
                     end
                      
                     // Fetching RDR (or Exception RDR)
                     fetch(); // build expected mem transaction
                     parse(); // update fields
                     execute(); // internal or external RDR_
                     
                     // Changing "first boot" status after the first rdr 
                     if (hws_ret_state == FIRST_BOOT)
                     begin
                       //read_hrr_regs(1,0,0);
                       hws_ret_state = NET_FETCH; 
                     end

                     // Read context (if branch dirty bit)
                     if (rdr_type == EXTERNAL) check_branch();


                     // Turn off PDs according to b2b bit
                     // dont check if soft awdt (pd keeps running)
                     if (vif.soft_awdt_expire === 1'b0)
                     begin
                        power_down_seq();
                     end
        
                     // if rrt_rd_cntr == 0 -> return to NET (b2b according to last RDR (from rrt))
                     if (rrt_rd_cntr_done == 1'b1)
                     begin
                        rrt_rd_cntr_done = 1'b0; // reset flag

                        `uvm_info (get_type_name(),$sformatf("net_rrt_sel = %s, hws_ret_state = %s",net_rrt_sel.name(), hws_ret_state.name()),verbosity);
                        if (net_rrt_sel != RRT || hws_ret_state != RRT_FETCH)
                        begin
                           `uvm_error(get_type_name(),$sformatf("rrt_rd_cntr_done is always from RRT"))
                        end
                        net_rrt_sel = NET; // net_rd_index++ is already done at previous net fetch TODO ??
                        hws_ret_state = NET_FETCH; // same as mem
                     end

 
                     `uvm_info (get_type_name(),$sformatf("************************** Finish executing RDR *******************************"),verbosity);

                  end // single rdr




                  // halt monitoring 
                  begin 
                     `uvm_info (get_type_name(),$sformatf("waiting for halt/reset"), verbosity);

                     @(posedge vif.du_hws_halt iff (vif.du_hws_halt===1'b1), negedge vif.adb_hws_rstn iff (vif.adb_hws_rstn===1'b0), posedge hard_awdt); // kills thread at halt OR hws reset of hard awdt
                     if (vif.adb_hws_rstn !== 1'b1) `uvm_info (get_type_name(),$sformatf("got hws_reset = 0x%0h", vif.adb_hws_rstn), verbosity);
                     if (vif.du_hws_halt  === 1'b1) `uvm_info (get_type_name(),$sformatf("got halt = 0x%0h", vif.du_hws_halt), verbosity);
                     if (hard_awdt === 1'b1) `uvm_info (get_type_name(),$sformatf("hard_awdt"), verbosity);

                     // reset mem read on halt
                     during_fetch_from_net = 1'b0; // indicates fetch is active
                     during_fetch_from_rrt = 1'b0; // indicates fetch is active
                     during_fetch_from_net_dbg_ram = 1'b0; // indicates fetch is active 
                     during_fetch_from_rrt_dbg_ram = 1'b0; // indicates fetch is active 

                     // TODO: YS: (tip) maybe on halt reset calls countres 
                  end

                join_any // single rdr or halt fork
                if (vif.du_hws_halt === 1'b1) disable fork; // kills all sub processes if halt 
                if (hard_awdt === 1'b1) disable fork; // kills all sub processes if hard awdt 
             end
             join // protection fork
 

          
         // if hard awdt -> break
         if (hard_awdt == 1'b1)  `uvm_info (get_type_name(),$sformatf("break because of hard AWDT"), verbosity);;
         if (hard_awdt == 1'b1) break;
         // if not back to back -> break
         // b2b need to be read from register and not RDR since SW can change it during SPU/CPU operation
         `uvm_info (get_type_name(),$sformatf("After RDR - SW_B2b = 0x%0h", field_backdoor_read("sw_b2ben")), verbosity);
         end while (
                    ((rdr_type == INTERNAL) && (b2bm == 1'b1)) 
                    ||
                    ((rdr_type == EXTERNAL) && (field_backdoor_read("sw_b2ben") == 1'b1))
                    ||
                    (vif.du_hws_halt === 1'b1)
                   ); // end of do-while loop 

//~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ end of main loop ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

         // for hard awdt no context write
         if (hard_awdt == 1'b0)
         begin

            check_timer = (timer_was_set_during_current_wave == 1'b1 || def_timer_enb == 1'b0) ? 1'b1 : 1'b0;

            // if default timert and no RTCC - set preset to default
            if (def_timer_enb == 1'b0)
            begin 
               if (!(timer_was_set_during_current_wave == 1'b1))
               begin
                  timer_index = 0; 
                  set_preset(calc_preset(), `__LINE__);
             `REG_WRITE_CHECK_START(hws_hrr_aon_timer_preset, hrr_aon_timer_preset, preset);
               end
            end

            // Store HWS context to ret  
            @(posedge vif.soc_clk iff (vif.soc_clk===1'b1)) // DRR shadow
            @(posedge vif.soc_clk iff (vif.soc_clk===1'b1)) // DRR shadow
            write_context();  
            
            // wait 1 cycle between done and power down 
            @(posedge vif.soc_clk iff (vif.soc_clk===1'b1)) 
            #1;
                    
            // If controlled by hws -> verify all domain are in reset and off
            if (vif.du_hws_prctl_sel === 1'b0)
            begin
               err_msg = " power domain is not in reset before Poff";
               if (vif.hws_clb_rstn !== 1'b0) `uvm_error(get_type_name(),{"clb" ,err_msg})
               if (vif.hws_isp_rstn !== 1'b0) `uvm_error(get_type_name(),{"isp", err_msg})
               if (vif.hws_mss_rstn !== 1'b0) `uvm_error(get_type_name(),{"mss", err_msg})
 
               err_msg = " power domain is not off before Poff";
               if (vif.hws_adb_clb_pgen !== 1'b0) `uvm_error(get_type_name(),{"clb" ,err_msg})
               if (vif.hws_adb_isp_pgen !== 1'b0) `uvm_error(get_type_name(),{"isp", err_msg})
               if (vif.hws_adb_mss_pgen !== 1'b0) `uvm_error(get_type_name(),{"mss", err_msg})
            end
            else
            begin
               // If controlled by TDRs -> verify all domain are ordint to TDR data
               err_msg = " power domain is not according to prctl";
               if (vif.hws_adb_clb_pgen !== du_pgen[2:2]) `uvm_error(get_type_name(),{"clb" ,err_msg})
               if (vif.hws_adb_isp_pgen !== du_pgen[1:1]) `uvm_error(get_type_name(),{"isp", err_msg})
               if (vif.hws_adb_mss_pgen !== du_pgen[0:0]) `uvm_error(get_type_name(),{"mss", err_msg})

               err_msg = " reset is not according to rstctl";
               if (vif.hws_clb_rstn !== du_rst[2:2]) `uvm_error(get_type_name(),{"clb" ,err_msg})
               if (vif.hws_isp_rstn !== du_rst[1:1]) `uvm_error(get_type_name(),{"isp", err_msg})
               if (vif.hws_mss_rstn !== du_rst[0:0]) `uvm_error(get_type_name(),{"mss", err_msg})
            end

            `uvm_info (get_type_name(),$sformatf("++++++++++++++++++++++++++ HWS goes to sleep ++++++++++++++++++++++++++"),verbosity);
//            repeat(20) @(posedge vif.soc_clk); // wait 20 soc clk for DRR write 
            // Waiting for FRC reset with watchdog   
            `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_switch_back_voltage_en), 2, "hws_adb_switch_back_voltage_en was not set before retention");
            if (vif.hrr_wkup_mode != 2'b10 ) begin //if cont we dont reset FRC and dont update sys_time in hrr
            `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_frc_rstn), 9, "frc reset was not set before retention");
            `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_self_poff), 2, "Timeout waiting for POFF");
            end
            // Waiting for POFF with watchdog       
            else         
                `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_self_poff), 11, "Timeout waiting for POFF");
           end // no hard awdt
         else
         begin
            hard_awdt = 0; // reset flag
            // reset values
            reset_vars();
            net_rrt_sel = NET; // first fetch from NVM
            hws_ret_state = FIRST_BOOT;
            net_rd_index = 0; // address in NVM (of 16 bit word) - 0 is  addr for first fetch 
            rrt_rd_index = 0; // address in ROM (of 16 bit word) 
         end
      end // big forever
   endtask // run_between_brownouts
   
   // ============================================
   //              fetch_from_net
   // ============================================
   // Monitor the NVM interface for read transaction (aka actual)
   // Backdor read from NET (aka expected)
   // Compare address (check the HWS)
   // Compare data (check the path from NVM)
   // 
   // Update RDR
   // increase NET index
   //
   // NET addr:
   // --------
   // NVM size is 4 KByte
   // NET is last 1/8 -> 4096*7/8 = 3584 = 0xe00
   
   task fetch_from_net();

      // NVM HW interface
      bit [15:0] nvm_hws_rdata;
      bit [7:0] hws_nvm_addr; 
      
      bit flag = 1'b0; // 0 - address phase ; 1 - data phase 
      
      // Backdoor read
      bit [31:0] data; 
      bit [31:0] addr = net_offset + net_rd_index*2; // index is byte address so x2 is for 16 bit data width
  
      // watchdog
      int wd = 0; 
   
      during_fetch_from_net = 1'b1;
 
      `uvm_info (get_type_name(),$sformatf("fetch_from_net"), verbosity);

//      fork
//         begin
//            #3000ns;
//            `uvm_fatal(get_type_name(), $sformatf("KILL ME")); 
//         end
//      join_none





      // Monitoring actual read transaction from NVM
      forever 
      begin
         // patch to solve problem if entering this task when hws_du_dbg_ram_sel is already high
         if (vif.soc_clk !== 1'b1) @(posedge vif.soc_clk);
         #1;
         wd++;
         if (wd > 100) 
            `uvm_error(get_type_name(),$sformatf("Timeout while waiting for NVM read (nvm_hw_rdy/hws_nvm_sel)"))

         if (vif.nvm_hw_rdy === 1'b1)
         begin
            // Monitoring Address
            if ((vif.hws_nvm_sel === 1'b1) && (flag == 1'b0))
            begin
               hws_nvm_addr = vif.hws_nvm_addr;
               `uvm_info (get_type_name(),$sformatf("NVM Read: Address phase %0d", vif.hws_nvm_addr), verbosity)
               flag = 1;
            end
            else
            // Monitoring Data
            begin
               if (flag == 1'b1)
               begin
                  if ($isunknown(vif.nvm_hws_rdata)) `uvm_fatal(get_type_name(), $sformatf("NVM read data <0x%0h> has X/Z (maybe soc_clk freq is > 10 MHz)", vif.nvm_hws_rdata)); 
                  nvm_hws_rdata = vif.nvm_hws_rdata;
                  `uvm_info (get_type_name(),$sformatf("NVM Read: Data phase 0x%0h", vif.nvm_hws_rdata), verbosity)
                  flag = 0;  
                  break;
               end
            end
         end 
         
         // patch to solve problem if entering this task when hws_du_dbg_ram_sel is already high
         @(negedge vif.soc_clk);
      end
         
      // Read from mvm model to get expected data 
      nvm.read(status, addr, data, UVM_BACKDOOR);
      
      case (net_rd_index%2)
         0: rdr = data[15:0];
          1: rdr = data[31:16];
      endcase 
      
      `uvm_info (get_type_name(),$sformatf("read from NVM [%0d]: index = %0d, data = 0x%0h", addr, net_rd_index, rdr), UVM_MEDIUM)
      
      // Compare actual to expected
      if (net_rd_index != hws_nvm_addr)
         `uvm_error(get_type_name(),$sformatf("Actual NET read address <%0d> is not <%0d> as expected",hws_nvm_addr, net_rd_index))

      if (rdr != nvm_hws_rdata)
         `uvm_error(get_type_name(),$sformatf("Actual NET read data <0x%0h> is not <0x%0h> as expected (net_rd_index = %0d)",nvm_hws_rdata, rdr, net_rd_index))
      
      // Increasing NET index for next RDR
      net_rd_index++;

      during_fetch_from_net = 1'b0; 
 
   endtask // fetch_from_nvm
   
   // ============================================
   //              fetch_from_rrt_dbg_ram
   // ============================================
   //  Monitor the RAM interface for read transaction (aka actual)
   //  Backdor read from RAM (aka expected)
   //  Compare address (check the HWS)
   //  Compare data (check the path from RAM)
   //  
   //  Update RDR
   //  increase ROM index
   //
   // RRT addr:
   // ---------
   // ROM size is 64 KByte
   // RRT starts @ 0xFC00 = 64,512
   
   task fetch_from_rrt_dbg_ram();

      // RAM HW interface
      bit [15:0] dbg_ram_rdata;
      bit [7:0] dbg_ram_addr; 
      
      bit flag = 1'b0; // 0 - address phase ; 1 - data phase 
      
      // Backdoor read
      bit [31:0] data; 
      bit [31:0] addr = 'hc00 +rrt_rd_index*2;
  
      // watchdog
      int wd = 0; 
      `uvm_info (get_type_name(),$sformatf("fetch_from_rrt_dbg_ram"), verbosity);
      during_fetch_from_rrt_dbg_ram = 1'b1; 
    
      // Monitoring actual read transaction from RAM
      forever 
      begin
         @(posedge vif.soc_clk);
         #1;
         wd++;
         if (wd > 100) 
            `uvm_error(get_type_name(),$sformatf("Timeout while waiting for RRT RAM read (ram_hw_rdy/hws_ram_sel)"))
          
         if (vif.hws_du_dbg_ram_sel === 1'b1)
         begin
            dbg_ram_addr = vif.hws_du_dbg_ram_addr;
            `uvm_info (get_type_name(),$sformatf("ROM Shadow Read: Address phase %0d", vif.hws_du_dbg_ram_addr), verbosity)
            @(posedge vif.soc_clk);
            #1ns; //cell delay - design can handle it 
            if (vif.hws_du_dbg_ram_sel === 1'b1)
            begin
               `uvm_error(get_type_name(),$sformatf("hws_du_dbg_ram_sel is high for more than 1 cycle"))
            end

            if (vif.du_hws_dbg_ram_rdvld === 1'b1)
            begin
               dbg_ram_rdata = vif.du_hws_dbg_ram_rdata;
               `uvm_info (get_type_name(),$sformatf("ROM shadow Read: Data phase 0x%0h", vif.du_hws_dbg_ram_rdata), verbosity)
               break;
            end
            else
            begin
               `uvm_error(get_type_name(),$sformatf("du_hws_dbg_ram_rdvld did not rise"))
            end
         end      
      end
         
      // Read from mvm model to get expected data 
      dbg_ram.read(status, addr, data, UVM_BACKDOOR);
      
      case (rrt_rd_index%2)
         0: rdr = data[15:0];
          1: rdr = data[31:16];
      endcase 
      
      `uvm_info (get_type_name(),$sformatf("read from ROM Shadow [%0d]: index = %0d, data = 0x%0h", addr, rrt_rd_index , rdr), UVM_MEDIUM)
      
      // Compare actual to expected
      if (rrt_rd_index != dbg_ram_addr)
         `uvm_error(get_type_name(),$sformatf("Actual ROM Shadow read address <%0d> is not <%0d> as expected",dbg_ram_addr, rrt_rd_index))

      if (rdr != dbg_ram_rdata)
         `uvm_error(get_type_name(),$sformatf("Actual ROM Shadow read data <0x%0h> is not <0x%0h> as expected (rrt_rd_index = %0d)",dbg_ram_rdata, rdr, rrt_rd_index))
      
      // Increasing RRT index for next RDR
      rrt_rd_index++;

      during_fetch_from_rrt_dbg_ram = 1'b0; 

   endtask // fetch_from_rrt shadow

   
   // ============================================
   //              fetch_from_net_dbg_ram
   // ============================================
   //  Monitor the NVM interface for read transaction (aka actual)
   //  Backdor read from NET (aka expected)
   //  Compare address (check the HWS)
   //  Compare data (check the path from NVM)
   //  
   //  Update RDR
   //  increase NET index
   //
   //  NET addr:
   //  --------
   //  NVM size is 4 KByte
   //  NET is last 1/8 -> 4096*7/8 = 3584 = 0xe00
   
   task fetch_from_net_dbg_ram();

      // NVM HW interface
      bit [15:0] dbg_ram_rdata;
      bit [7:0] dbg_ram_addr; 
      
      bit flag = 1'b0; // 0 - address phase ; 1 - data phase 
      
      // Backdoor read
      bit [31:0] data; 
      bit [31:0] addr = net_offset + net_rd_index*2; // // TODO:index is byte address so x2 is for 16 bit data width
  
      // watchdog
      int wd = 0; 
      `uvm_info (get_type_name(),$sformatf("fetch_from_net_dbg_ram"), verbosity);
      during_fetch_from_net_dbg_ram = 1'b1; 
    
      // Monitoring actual read transaction from NVM
      forever 
      begin
         // patch to solve problem if entering this task when hws_du_dbg_ram_sel is already high
         if (vif.soc_clk !== 1'b1) @(posedge vif.soc_clk);
         #1;
         wd++;
         if (wd > 100) 
            `uvm_error(get_type_name(),$sformatf("Timeout while waiting for NVM read (nvm_hw_rdy/hws_nvm_sel)"))


          
         if (vif.hws_du_dbg_ram_sel === 1'b1)
         begin
            dbg_ram_addr = vif.hws_du_dbg_ram_addr;
            `uvm_info (get_type_name(),$sformatf("NVM Read: Address phase %0d", vif.hws_du_dbg_ram_addr), verbosity)
            @(posedge vif.soc_clk);
            #1ns; //cell delay - design can handle it 
            if (vif.hws_du_dbg_ram_sel === 1'b1)
            begin
               `uvm_error(get_type_name(),$sformatf("hws_du_dbg_ram_sel is high for more than 1 cycle"))
            end

            if (vif.du_hws_dbg_ram_rdvld === 1'b1)
            begin
               dbg_ram_rdata = vif.du_hws_dbg_ram_rdata;
               `uvm_info (get_type_name(),$sformatf("NVM Read: Data phase 0x%0h", vif.du_hws_dbg_ram_rdata), verbosity)
               break;
            end
            else
            begin
               `uvm_error(get_type_name(),$sformatf("du_hws_dbg_ram_rdvld did not rise"))
            end
         end 

         // patch to solve problem if entering this task when hws_du_dbg_ram_sel is already high (see also beining of task)
         @(negedge vif.soc_clk);
     
      end
         
      // Read from mvm model to get expected data 
      dbg_ram.read(status, addr, data, UVM_BACKDOOR);
      
      case (net_rd_index%2)
         0: rdr = data[15:0];
          1: rdr = data[31:16];
      endcase 
      
      `uvm_info (get_type_name(),$sformatf("read from NVM [%0d]: index = %0d, data = 0x%0h", addr, net_rd_index, rdr), UVM_MEDIUM)
      
      // Compare actual to expected
      if (net_rd_index != dbg_ram_addr)
         `uvm_error(get_type_name(),$sformatf("Actual NET read address <%0d> is not <%0d> as expected",dbg_ram_addr, net_rd_index))

      if (rdr != dbg_ram_rdata)
         `uvm_error(get_type_name(),$sformatf("Actual NET read data <0x%0h> is not <0x%0h> as expected (net_rd_index = %0d)",dbg_ram_rdata, rdr, net_rd_index))
      
      // Increasing NET index for next RDR
      net_rd_index++;

      during_fetch_from_net_dbg_ram = 1'b0; 
         


   endtask // fetch_from_nvm

   
   // ============================================
   //              fetch_from_rrt
   // ============================================
   
   // Monitor the ROM interface for read transaction (aka actual)
   // Backdor read from RRT (aka expected)
   // Compare address (check the HWS)
   // Compare data (check the path from ROM)
   // 
   // Update RDR
   // increase NET index
   //
   //
   // RRT addr:
   // ---------
   // ROM size is 64 KByte
   // RRT starts @ 0xFC00 = 64,512

   task fetch_from_rrt();
      
      // Backdoor read
      bit [31:0] data; 
      bit [31:0] addr = rrt_offset + rrt_rd_index*2;
      
      //  ROM HW interface
      bit [15:0] rom_hws_rdata;
      bit [8:0] hws_rom_addr;
      `uvm_info (get_type_name(),$sformatf("fetch_from_rrt"), verbosity);
   
      during_fetch_from_rrt = 1'b1; 
  
      // Actual HW if - addr
      if (vif.hws_rom_sel !== 1'b1) @(posedge vif.hws_rom_sel);
      #1ns // wait for stable data
      hws_rom_addr = vif.hws_rom_addr;
      
      `uvm_info (get_type_name(),$sformatf("ROM Read: Address phase %0d", vif.hws_rom_addr), verbosity)

      // Actual HW if - data
      if (vif.rom_hw_rdvld !== 1'b1) @(posedge vif.rom_hw_rdvld);
      #2ns // wait for stable data
      rom_hws_rdata = vif.rom_hws_rdata;
      `uvm_info (get_type_name(),$sformatf("ROM Read: Data phase 0x%0h", vif.rom_hws_rdata), verbosity)
               
      // Read from mvm model to get expected data 
      rom.read(status, addr, data, UVM_BACKDOOR);
      
      case (rrt_rd_index%2)
         0: rdr = data[15:0];
         1: rdr = data[31:16];
      endcase 
      
      `uvm_info (get_type_name(),$sformatf("read from ROM [%0d]: index = %0d, data = 0x%0h", addr, rrt_rd_index, rdr), UVM_MEDIUM)
      
      // Compare actual to expected
      if (rrt_rd_index != hws_rom_addr)
         `uvm_error(get_type_name(),$sformatf("Actual RRT read address <%0d> is not <%0d> as expected",hws_rom_addr, rrt_rd_index))

      if (rdr != rom_hws_rdata)
         `uvm_error(get_type_name(),$sformatf("Actual RRT read data <0x%0h> is not <0x%0h> as expected (rrt_rd_index = %0d)",rom_hws_rdata, rdr, rrt_rd_index))      
      
      // Increasing RRT index for next RDR
      rrt_rd_index++;

      during_fetch_from_rrt = 1'b0;
      if (rrt_rd_cntr > 0)
      begin
         rrt_rd_cntr--;
         `ifdef HWS_DBG vif.debug_rrt_rd_cntr = rrt_rd_cntr; `endif
         if (rrt_rd_cntr == 0)
         begin
            rrt_rd_cntr_done = 1'b1;
         end
      end
   endtask // fetch_from_rrt
   
   
   // ============================================
   //            Detect_exception()
   // ============================================
   // On beginning of active check if exception raised during retention
   // If exception occurred -> set exception flag
   task detect_exception();

      bit nrg_det_exception;
      bit timer_exception;
      bit rwdt_exception;

      // nrg_det/timer exceptions can only occure during retention 
      // We check for exceptions only at the first fetch of active wave
      if (start_of_active_flag == 1'b1)
      begin
            `uvm_info ("REGS1",$sformatf("field_backdoor_read(hrr_timer_except_en) = 0x%0h", field_backdoor_read("hrr_timer_except_en")), UVM_MEDIUM);
         nrg_det_exception = vif.adb_hws_nrg_det_stat          && field_backdoor_read("hrr_envdet_except_en");            
         timer_exception   = vif.adb_hws_timer_done            && field_backdoor_read("hrr_timer_except_en");
         rwdt_exception    = vif.adb_hws_rwdt_expire_exception; // no exception en - it is allways on
            `uvm_info ("REGS2",$sformatf("field_backdoor_read(hrr_timer_except_en) = 0x%0h", field_backdoor_read("hrr_timer_except_en")), UVM_MEDIUM);

         if (nrg_det_exception)
         begin
            `uvm_info (get_type_name(),$sformatf("HWS got nrg_det exception"), UVM_MEDIUM);
             mailbox.cov("nrg_det_exception");
            `REG_WRITE_CHECK_START(excphndlr_nrgdet_exception_cause_status, nrgdet_exception_cause_status, 1);
         end
         else
         begin
            if (field_backdoor_read("nrgdet_exception_cause_status") != 1'b0) `uvm_error(get_type_name(),$sformatf("nrgdet_exception_cause_status is 1 but no got exception"))
         end 

         if (timer_exception)
         begin
            `uvm_info (get_type_name(),$sformatf("HWS got timer exception"), UVM_MEDIUM);
             mailbox.cov("timer_exception");
            `REG_WRITE_CHECK_START(excphndlr_timer_exception_cause_status, timer_exception_cause_status, 1);
         end
         else
         begin
            if (field_backdoor_read("timer_exception_cause_status") != 1'b0) `uvm_error(get_type_name(),$sformatf("timer_exception_cause_status is 1 but no got exception"))
         end 
         
         if (rwdt_exception)
         begin
            `uvm_info (get_type_name(),$sformatf("HWS got rwdt exception"), UVM_MEDIUM);
             mailbox.cov("rwdt_exception");
            `REG_WRITE_CHECK_START(excphndlr_rwdt_exception_cause_status, rwdt_exception_cause_status, 1);
         end
         else
         begin
            if (field_backdoor_read("rwdt_exception_cause_status") != 1'b0) `uvm_error(get_type_name(),$sformatf("rwdt_exception_cause_status is 1 but no got exception"))
         end 

         if (nrg_det_exception || timer_exception || rwdt_exception)
         begin

            `uvm_info (get_type_name(),$sformatf("nrg_det_exception = 0x%0h, timer_exception = 0x%0h, rwdt_exception = 0x%0h",nrg_det_exception, timer_exception, rwdt_exception), UVM_MEDIUM);

            exception_flag = 1; // Indicates exception occurred
            exception_rdr = 0;  // Reset rdr to be on the safe side


            case (field_backdoor_read("hrr_except_pu_sel"))
               // SPU
               0: 
               begin
                  case (field_backdoor_read("hrr_except_memory_sel"))
                     // SPU ROM
                     0:
                     begin
                        `uvm_info (get_type_name(),$sformatf("SPU ROM"), UVM_MEDIUM);

                        mailbox.cov("spu_rom_ex");
                        exception_rdr[15] = 1'h0;    // B2bm         // TODO YS: not sure it is b2b, check with YuvalA                   
                        exception_rdr[14:13] = 2'h2; // SPU ROM
                        exception_rdr[12:0] = 13'h1f7f; // PC this is the pointer for a long branch to function in SPU ROM called "exception handler 
                     end

                     // SPU NVM
                     1:
                     begin
                        mailbox.cov("spu_nvm_ex");

                        exception_rdr[15] = 1'h0;    // B2bm         // TODO YS: not sure it is b2b, check with YuvalA                   
                        exception_rdr[14:12] = 3'h7; // SPU ROM
                        exception_rdr[11] = 1'h0;    // RSEL = NVM
                        exception_rdr[10] = 1'h0;    // reserved - don'tcare but make sure same as design 
                        exception_rdr[9:0] = 10'h0;  // INDEX        // TODO YS: check for address or get define 
                     end

                     default: `uvm_error(get_type_name(),$sformatf("hrr_except_memory_sel <0x%0h> is not 0 or 1",field_backdoor_read("drr_except_memory_sel")))
                  endcase
               end

               // CPU
               1: 
               begin
                  case (field_backdoor_read("drr_except_memory_sel"))
                     // CPU ROM
                     0:
                     begin
                        if (mailbox.test_goals.exists("cpu_rom_ex")) mailbox.test_goals["cpu_rom_exception"]--;
                        exception_rdr[15] = 1'h0;    // B2bm         // TODO YS: not sure it is b2b, check with YuvalA                   
                        exception_rdr[14:13] = 2'h1; // CPU ROM
                        exception_rdr[12:0] = 13'h0; // PC           // TODO YS: check for address or get define 
                     end

                     // CPU NVM
                     1:
                     begin
                        if (mailbox.test_goals.exists("cpu_nvm_ex")) mailbox.test_goals["cpu_nvm_exception"]--;
                        exception_rdr[15] = 1'h0;    // B2bm         // TODO YS: not sure it is b2b, check with YuvalA                   
                        exception_rdr[14:12] = 3'h6; // CPU ROM
                        exception_rdr[11:10] = 2'h0; // reserved - don'tcare but make sure same as design 
                        exception_rdr[9:0] = 10'h0;  // INDEX        // TODO YS: check for address or get define 
                     end
                     default: `uvm_error(get_type_name(),$sformatf("hrr_except_memory_sel <0x%0h> is not 0 or 1",field_backdoor_read("drr_except_memory_sel")))
                  endcase

               end
          
               default: `uvm_error(get_type_name(),$sformatf("hrr_except_pu_sel <0x%0h> is not 0 or 1",field_backdoor_read("hrr_except_pu_sel")))

            endcase
         end // if exception
      end // if start of active

      start_of_active_flag = 1'b0; // Reset indication
   endtask
 


   // ============================================
   //                Fetch();
   // ============================================
   // Fetch RDR from selected memory 
   task fetch();
      `uvm_info (get_type_name(),$sformatf("fetch: exception_flag = 0x%0h, net_rrt_sel = %s, du_hws_dbgramctl_nvmen = 0x%0h", exception_flag, net_rrt_sel.name(), vif.du_hws_dbgramctl_nvmen), verbosity);

      // No exception - fetch from memory
      if (exception_flag == 1'b0)
      begin 
         case (net_rrt_sel)
            NET: 
            begin
               if (vif.du_hws_dbgramctl_nvmen === 1'b0) 
               begin
                  fetch_from_net();
               end
               else
               begin
                  fetch_from_net_dbg_ram();
               end
            end

            RRT: 
            begin
               if (vif.du_hws_dbgramctl_hwsen === 1'b0) 
               begin
                  fetch_from_rrt();
               end
               else
               begin
                  fetch_from_rrt_dbg_ram();
               end
            end
         endcase
      end
      else
      begin
         // Exception
         rdr = exception_rdr;         
         `uvm_info (get_type_name(),$sformatf("Exception RDR (0x%0h) was fetched", rdr), UVM_MEDIUM);
         exception_flag = 0;
         repeat(1) @(posedge vif.soc_clk); // wait some time for the write of exception cause 

      end
   endtask;
           
   // ============================================
   //              Parse
   // ============================================ 
   // Parse RDR 
   task parse();  

      // sapmled vals - this function can be called in paralel
      bit b2bm_s;
      bit bpdo_s;
 
      if (rdr[14:12] == 3'b000)
      begin
         rdr_type = INTERNAL;
         parse_internal();
      end
      else 
      begin
         rdr_type = EXTERNAL;
         parse_external();
      end

      // After parse check write to internal registers
      // These registers does not have external i/f so we use backdoor
      fork
         begin
            b2bm_s = b2bm;
            bpdo_s = bpdo;
            repeat(3) @(posedge vif.soc_clk); // wait some time for the write
            field_backdoor_read_and_check("sw_b2ben",  b2bm_s, `__LINE__);
            field_backdoor_read_and_check("sw_b2bpdo", bpdo_s, `__LINE__);
         end 
      join_none
   endtask // parse
  
   // ============================================
   //              Parse internal
   // ============================================
   // Parsing internal RDRs
      task parse_internal();  
     
         b2bm = rdr[15:15];
         bpdo = 0;
         prefix = $sformatf("Parse%0sinternal RDR of type", b2bm == 1 ? " B2B " : " "); // string used for printing
         case(rdr[11:9])
               
            // EOL (End Of Line)
            3'b000:
            begin
               internal_name = "EOL";
               nri = rdr[7:0];
               `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", internal_name, nri); `endif
               `uvm_info(get_type_name(), $sformatf("%s EOL: nri = 0x%0h", prefix, nri), verbosity);
            end
               
            // GIC
            3'b001:
            begin
               internal_name = "GIC";
               cfr = rdr[7:4];
               vgr = rdr[3:0];
               `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s", internal_name); `endif
               `uvm_info(get_type_name(), $sformatf("%s GIC: cfr = 0x%0h, vgr = 0x%0h", prefix, cfr, vgr), verbosity);
            end
               
            // RPDC
            3'b010:
            begin
               internal_name = "RPDC";
               rrt_counter = rdr[7:0];
               `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", internal_name, rrt_counter); `endif
               `uvm_info(get_type_name(), $sformatf("%s RPDC: rrt_counter = 0x%0h", prefix, rrt_counter), verbosity);
            end
               
            // RPDI
            3'b011:
            begin
               internal_name = "RPDI";
               rri = rdr[8:0];
               `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", internal_name, rri); `endif
               `uvm_info(get_type_name(), $sformatf("%s RPDI: rri = 0x%0h", prefix, rri), verbosity);
            end
               
            // NOP
            3'b100:
            begin
               internal_name = "NOP";
               // Reserved
               `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s", internal_name); `endif
               `uvm_info(get_type_name(), $sformatf("%s NOP: ", prefix), verbosity);
            end
               
            // RTCC
            3'b101:
            begin
               internal_name = "RTCC";
               frc_reset = rdr[7:7];
               timer_mode = rdr[6:4];
               timer_index = rdr[3:2];
               wake_up_mode = rdr[1:0];
               `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s", internal_name); `endif
               `uvm_info(get_type_name(), $sformatf("%s RTCC: frc_reset = 0x%0h, timer_mode = 0x%0h, timer_index = 0x%0h, wake_up_mode = 0x%0h", prefix, frc_reset, timer_mode, timer_index, wake_up_mode), verbosity);
               if (timer_mode inside {3,4} && wake_up_mode == 0)
               begin 
                  `uvm_error(get_type_name(),$sformatf("Timer#%0d without wakeup is forbidden", timer_mode))
               end
            end
               
            default: `uvm_error(get_type_name(),$sformatf("Internal command header <0x%0h> is not defined ",rdr[11:9]))

         endcase // internal command header
      endtask // parse_internal
      
   // ============================================
   //              Parse external
   // ============================================
   // Parsing external RDRs
   task parse_external();
   
      string prefix;

   
      // Back to back for all types of RDRs is bit 15
      b2bm = rdr[15:15];
      prefix = $sformatf("Parse%0sexternal RDR of type", b2bm == 1 ? " B2B " : " "); // string used for printing
   
      case (rdr[14:12])
               
         // PU Command
         3'b001: 
         begin
            psi = rdr[11:10];
            bpdo = rdr[9:9];
            pu_cmd = rdr[8:0];
            
            case (psi)
               2'b00: external_rdr_type = FLL_RDR;         
               2'b01: external_rdr_type = PGX_RDR; 
               2'b10: external_rdr_type = FMU_RDR; 
               2'b11: external_rdr_type = SEC_RDR; 
               default: `uvm_error(get_type_name(),$sformatf("PSI command <0x%0h> is not defined ",psi))      
            endcase
            `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", external_rdr_type.name(), pu_cmd); `endif
            
            `uvm_info(get_type_name(), $sformatf("%s PU: psi = 0x%0h, bpdo = 0x%0h, pu_cmd = 0x%0h", prefix, psi, bpdo, pu_cmd), verbosity);
         end
         
         // CPU ROM
         3'b010, 3'b011: 
         begin
            external_rdr_type = CPU_ROM_RDR;
            bpdo = 0; // no bpdo bit on SW RDR
            cpu_rom_pc = rdr[12:0];
            cpu_rom_cmd = {1, cpu_rom_pc}; // bit 13 is 1 to indicate ROM
            `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", external_rdr_type.name(), cpu_rom_pc); `endif
            `uvm_info(get_type_name(), $sformatf("%s CPU ROM: cpu_rom_pc = 0x%0h", prefix, cpu_rom_pc), verbosity);
         end
         
         // SPU ROM
         3'b100, 3'b101: 
         begin
            external_rdr_type = SPU_ROM_RDR;
            bpdo = 0; // no bpdo bit on SW RDR
            spu_rom_index = rdr[12:0];
            spu_rom_cmd = {1, spu_rom_index}; // bit 13 is 1 to indicate ROM
            `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", external_rdr_type.name(), spu_rom_cmd); `endif
            `uvm_info(get_type_name(), $sformatf("%s SPU ROM: spu_rom_index = 0x%0h", prefix, spu_rom_index), verbosity);
         end
         
         // CPU NVM
         3'b110: 
         begin
            external_rdr_type = CPU_NVM_RDR;
            bpdo = 0; // no bpdo bit on SW RDR
            cpu_nvm_pc = rdr[11:0];
            cpu_nvm_cmd = {2'b0, cpu_nvm_pc}; // padding to 14 bits
            `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", external_rdr_type.name(), cpu_nvm_cmd); `endif
            `uvm_info(get_type_name(), $sformatf("%s CPU NVM: cpu_nvm_pc = 0x%0h", prefix, cpu_nvm_pc), verbosity);
         end
         
         // SPU NVM
         3'b111: 
         begin
            external_rdr_type = SPU_NVM_RDR;
            bpdo = 0; // no bpdo bit on SW RDR
            spu_nvm_index = rdr[11:0];
            spu_nvm_cmd = {2'b0, spu_nvm_index}; // padding to 14 bits
            `ifdef HWS_DBG vif.debug_rdr = $sformatf("%s <0x%0h>", external_rdr_type.name(), spu_nvm_cmd); `endif
            `uvm_info(get_type_name(), $sformatf("%s SPU NVM: spu_nvm_index = 0x%0h", prefix, spu_nvm_index), verbosity);
         end
         
         default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))
        
      endcase // rdr command header
         
   endtask; // parse 
   
   // ============================================
   //                execute
   // ============================================
   task execute();
      case(rdr_type)
         INTERNAL : execute_internal();
         EXTERNAL : execute_external();
      endcase
   endtask // execute
   
   // ============================================
   //            execute_internal()
   // ============================================
   // Checkers for data write to ret according to the internal command
   task execute_internal();

      `uvm_info(get_type_name(), $sformatf("Executing internal RDR of type: %s", internal_name), UVM_MEDIUM);

      case (internal_name)
         
         // If from rrt + nri = 0 -> go to net_rd_index+1 
         // If from rrt + nri != 0 -> go to nri
         // If from net go to nri 
         "EOL" : 
         begin
            case (net_rrt_sel)
               RRT:
               begin
                  net_rrt_sel = NET; // net_rd_index++ is already done at previous net fetch
                  hws_ret_state = NET_FETCH; // same as mem
                  if (nri != 0 ) net_rd_index = nri;
//                  rrt_rd_index--; // rrt index is dontcare but design keeps it as last index so since we increased it after fetch we have to decrease 
                  if (b2bm == 0) rrt_rd_index--; 
               end
            
               NET:
               begin
                  net_rd_index = nri;
                  mailbox.routine_cnt++; // EOL from NET means HWS compleated a routine
                  `uvm_info(get_type_name(), $sformatf("routine_cnt = %0d, routine_num = %0d", mailbox.routine_cnt, mailbox.routine_num), UVM_NONE);
               end
               
               default: `uvm_error(get_type_name(),$sformatf("Mem = %s is undefined", net_rrt_sel.name()))
            endcase 
         end
         
         "GIC" : 
         begin
            `uvm_error(get_type_name(),$sformatf("Internal RDR of type %s not implemented yet", internal_name))
         end
         
         "RPDC": 
         begin
            rrt_rd_cntr = rrt_counter;
            rrt_rd_cntr_done = 1'b0;
            `ifdef HWS_DBG vif.debug_rrt_rd_cntr = rrt_rd_cntr; `endif
            //`uvm_error(get_type_name(),$sformatf("Internal RDR of type %s not implemented yet", internal_name))
         end
         
         // Next fetch will be from ROM @ index rri 
         "RPDI": 
         begin 
            net_rrt_sel = RRT;
            hws_ret_state = RRT_FETCH; // same as mem
            rrt_rd_index = rri;
         end
         
         "NOP" : 
         begin
            `uvm_error(get_type_name(),$sformatf("Internal RDR of type %s not implemented yet", internal_name))
         end
         
         // Update retention fields 
         // TODO: timers indication before poff
         // TODO default timer 
         "RTCC": 
         begin

            if (timer_mode inside {1,3,4,5,6,7}) timer_was_set_during_current_wave = 1'b1;
            
            case (timer_mode)
               // NoAction 
               0 : 
               begin                        
          
               end
            
               //DEF_TIMER_ENB=0x0,TIMER_EXCEPT_EN=0x0,VSTART_COUNT_TIMER_ENB=0x1,PACE_ENB=0x1,PEND_VSTART=0x1
               1 : 
               begin  
                  def_timer_enb          = 1'b0;  
                  timer_except_en        = 1'b0;  
                  vstart_count_timer_enb = 1'b1;  
                  pace_enb               = 1'b1;
                  pend_vstart            = 1'b1;  
               end
               
               // DEF_TIMER_ENB=0x1,TIMER_EXCEPT_EN=0x0,VSTART_COUNT_TIMER_ENB=0x1,PACE_ENB=0x1,PEND_VSTART=0x1
               2 : 
               begin  
                  def_timer_enb          = 1'b1;  
                  timer_except_en        = 1'b0;  
                  vstart_count_timer_enb = 1'b1;  
                  pace_enb               = 1'b1;  
                  pend_vstart            = 1'b1;  
               end
               
               // DEF_TIMER_ENB=0x1,TIMER_EXCEPT_EN=0x1,VSTART_COUNT_TIMER_ENB=0x0,PACE_ENB=0x1,PEND_VSTART=0x1
               3 : 
               begin  
                  def_timer_enb          = 1'b1;  
                  timer_except_en        = 1'b1;  
                  vstart_count_timer_enb = 1'b0;  
                  pace_enb               = 1'b1;  
                  pend_vstart            = 1'b1;  
               end
               
               // DEF_TIMER_ENB=0x1,TIMER_EXCEPT_EN=0x0,VSTART_COUNT_TIMER_ENB=0x0,PACE_ENB=0x1,PEND_VSTART=0x1
               4 : 
               begin  
                  def_timer_enb          = 1'b1;  
                  timer_except_en        = 1'b0;  
                  vstart_count_timer_enb = 1'b0;  
                  pace_enb               = 1'b1;  
                  pend_vstart            = 1'b1;  
               end
               
               // DEF_TIMER_ENB=0x1,TIMER_EXCEPT_EN=0x0,VSTART_COUNT_TIMER_ENB=0x1,PACE_ENB=0x0,PEND_VSTART=0x0
               5 : 
               begin  
                  def_timer_enb          = 1'b1;  
                  timer_except_en        = 1'b0;  
                  vstart_count_timer_enb = 1'b1;  
                  pace_enb               = 1'b0;  
                  pend_vstart            = 1'b0;  
               end
               
               // DEF_TIMER_ENB=0x1,TIMER_EXCEPT_EN=0x1,VSTART_COUNT_TIMER_ENB=0x1,PACE_ENB=0x0,PEND_VSTART=0x0
               6 : 
               begin  
                  def_timer_enb          = 1'b1;  
                  timer_except_en        = 1'b1;  
                  vstart_count_timer_enb = 1'b1;  
                  pace_enb               = 1'b0;  
                  pend_vstart            = 1'b0;  
               end
               
               // DEF_TIMER_ENB=0x1,TIMER_EXCEPT_EN=0x0,VSTART_COUNT_TIMER_ENB=0x1,PACE_ENB=0x0,PEND_VSTART=0x1
               7 :    
               begin  
                  def_timer_enb          = 1'b1;  
                  timer_except_en        = 1'b0;  
                  vstart_count_timer_enb = 1'b1;  
                  pace_enb               = 1'b0;  
                  pend_vstart            = 1'b1;  
               end
            endcase



            // Because internal have zero time execute (parse-> done) I need to open a new thread 
            fork
               begin
                     
                  // frc reset - rise frc_reset signal
                  if (frc_reset == 1'b1) 
                  begin
                     `uvm_error(get_type_name(),$sformatf("frc reset from rtcc is no longer POR - frc is reset any retention", internal_name))
                  end 
                 
                  `REG_WRITE_CHECK_START(drr1_shadow_def_timer_enb,          def_timer_enb,          def_timer_enb); 
                  `REG_WRITE_CHECK_START(hws_hrr_timer_except_en,            hrr_timer_except_en,    timer_except_en); 
                  `REG_WRITE_CHECK_START(drr0_shadow_vstart_count_timer_enb, vstart_count_timer_enb, vstart_count_timer_enb); 
                  `REG_WRITE_CHECK_START(drr1_shadow_pace_enb,               pace_enb,               pace_enb); 
                  `REG_WRITE_CHECK_START(drr1_shadow_pend_vstart,            pend_vstart,            pend_vstart); 

                  // According to timer index need to sel clock 
                  if (timer_mode inside {1,3,4,5,6,7})
                  begin 

                     case (timer_index)
                        0: `REG_WRITE_CHECK_START(drr0_shadow_timer_clk_sel, timer_clk_sel, 2'b00) // div 1
                        1: `REG_WRITE_CHECK_START(drr0_shadow_timer_clk_sel, timer_clk_sel, 2'b00) // div 1
                        2: `REG_WRITE_CHECK_START(drr0_shadow_timer_clk_sel, timer_clk_sel, 2'b01) // div 4
                        3: `REG_WRITE_CHECK_START(drr0_shadow_timer_clk_sel, timer_clk_sel, 2'b10) // div 16
                     endcase
                  end
 
                  // Preset set according to timer index (part of rtcc)
                  if (timer_mode != 0)
                  begin
                     `uvm_info(get_type_name(), $sformatf("Calc from RTCC"), UVM_MEDIUM);
                     if (timer_mode == 2) set_preset(0, `__LINE__); 
                     else                 set_preset(calc_preset(), `__LINE__); 

                     preset_s = preset; // sampeling preset in order to solve race
                     `REG_WRITE_CHECK_START(hws_hrr_aon_timer_preset, hrr_aon_timer_preset, preset_s);
                  end 
                  
                  // wakeup mode - write to regs
                  `REG_WRITE_CHECK_START(hws_hrr_wkup_mode, hrr_wkup_mode, wake_up_mode); 
               end
            join_none 
            #1ns; // YS: This delay is a MUST for the fork to begin! DO NOT REMOVE IT!!!!!!!
         end
         
         default: `uvm_error(get_type_name(),$sformatf("Internal RDR of type %s is not defined", internal_name))


      endcase

      // If this current internal rdr cancelled b2b, wait untill b2b = 0
      if ((b2bm == 0) && (vif.sw_b2ben === 1'b1))
      begin
         `SIGNAL_WATCHDOG(wait(vif.sw_b2ben === 1'b0), 5, "sw_b2ben fall WD");
      end

   endtask // execute_internal()
   
   // ============================================
   //          execute_external
   // ============================================
   // 1. wait for go (error after timeout)
   // 2. check CIF command
   // 3. wait for done (error after timeout)
   // CIF protocol is checked in cif_checker
   
   task execute_external();
      string msg; // for error printing
      
      // Set pu_name for printing    
      set_pu_name();
      msg = $sformatf("%0sexternal RDR of type: %s", (b2bm == 1 ? " B2B " : " "), pu_name); 
      `uvm_info(get_type_name(), $sformatf("Executing%s", msg), UVM_MEDIUM);
      
      
      // Set power domains on/of according to RDR (implicit)
      case (external_rdr_type)
         FLL_RDR:     begin clbpd = 1; msspd = 0; isppd = 0; end            
         PGX_RDR:     begin clbpd = 0; msspd = 0; isppd = 0; end
         FMU_RDR:     begin clbpd = 1; msspd = 0; isppd = 0; end
         SEC_RDR:     begin clbpd = 0; msspd = 0; isppd = 0; end
         CPU_ROM_RDR: begin clbpd = 0; msspd = 1; isppd = 1; end
         SPU_ROM_RDR: begin clbpd = 0; msspd = 0; isppd = 1; end
         CPU_NVM_RDR: begin clbpd = 0; msspd = 1; isppd = 1; end
         SPU_NVM_RDR: begin clbpd = 0; msspd = 0; isppd = 1; end           
         default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))   
      endcase // rdr command header
    
      `uvm_info(get_type_name(), $sformatf("bpdo = 0x%0h, sw_bpdo  = 0x%0h", bpdo, field_backdoor_read("sw_b2bpdo")), verbosity);

      // Keep on or turn off SW PDs accordig BPDO bit
      if (bpdo == 1 || sw_bpdo == 1) 
      begin
         if (mailbox.test_goals.exists("bpdo")) mailbox.test_goals["bpdo"]--; 
         msspd = 0;
         isppd = 0;
         sw_bpdo = 0; // reset FLAG
      end
      else
      begin
         // Update SW power domains that kept on from prev RDR (only b2b mode)
         msspd |= msspd_prev;      
         isppd |= isppd_prev;      
      end

      // Update HW power domains that kept on from prev RDR (only b2b mode) 
      clbpd |= clbpd_prev;  

      // Without considering bpdo - current RDR PD must be on 
      if (external_rdr_type inside {CPU_ROM_RDR, CPU_NVM_RDR}) msspd = 1; 
      if (external_rdr_type inside {SPU_ROM_RDR, SPU_NVM_RDR}) isppd = 1;

   
      
      // Before power up sequence, checking writing to pgen registers
      pgen_regs_checker(`__LINE__);
      
      // YS: I see 2 cycles before power sequence - not sure if needed
      repeat (2) @(posedge vif.soc_clk);
      power_up_sequence();

      // Wait for GO to PU
      `uvm_info(get_type_name(), $sformatf("Wait for go"), verbosity) 
      wait_for_go();

      // format msg for power logging
      msg = $sformatf("%0s%s", (b2bm == 1 ? " B2B " : " "), pu_name); 
 
      case (external_rdr_type)
         FLL_RDR:     msg = $sformatf("%s (command = 0x%0h)", msg, pu_cmd);       
         PGX_RDR:     msg = $sformatf("%s (command = 0x%0h)", msg, pu_cmd);  
         FMU_RDR:     msg = $sformatf("%s (command = 0x%0h)", msg, pu_cmd); 
         SEC_RDR:     msg = $sformatf("%s (command = 0x%0h)", msg, pu_cmd);
         CPU_ROM_RDR: msg = $sformatf("%s (command = 0x%0h)", msg, cpu_rom_cmd); 
         SPU_ROM_RDR: msg = $sformatf("%s (command = 0x%0h)", msg, spu_rom_cmd); 
         CPU_NVM_RDR: msg = $sformatf("%s (command = 0x%0h)", msg, cpu_nvm_cmd); 
         SPU_NVM_RDR: msg = $sformatf("%s (command = 0x%0h)", msg, spu_nvm_cmd);
         default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))   
      endcase // rdr command header   
      
      if (cfg.power_mon_en)
      begin
         `uvm_info("PWR_LOG", $sformatf(""), UVM_NONE) // power logging
         `uvm_info("PWR_LOG", $sformatf("Go%s", msg), UVM_NONE) // power logging
      // measure soc_clk for power logging
          measure_soc_clock();
      end

      isppd_at_go = field_backdoor_read("pgen_isp");
      msspd_at_go = field_backdoor_read("pgen_mss");
      `uvm_info(get_type_name(), $sformatf("Got go"), verbosity) 
      
      // Check command 
      check_cif_cmd();
      
      // Wait for PU return DONE
      wait_for_done();

      if (cfg.power_mon_en)
      begin
         `uvm_info("PWR_LOG", $sformatf("Done%s", msg), UVM_NONE) // power logging  
         `uvm_info("PWR_LOG", $sformatf(""), UVM_NONE) // power logging
      end

      isppd_at_done = field_backdoor_read("pgen_isp");
      msspd_at_done = field_backdoor_read("pgen_mss");



      if (b2bm == 1'b0 && field_backdoor_read("sw_b2ben") == 1'b1) 
      begin
         `uvm_info(get_type_name(), $sformatf("SW wrote 1 to b2b bit"), verbosity)   
         b2bm = 1'b1; 
      end
      
      if (b2bm == 1'b1 && field_backdoor_read("sw_b2ben") == 1'b0)
      begin
         `uvm_info(get_type_name(), $sformatf("SW wrote 0 to b2b bit"), verbosity)   
         b2bm = 1'b0; 
      end

      // BPDO
      if (bpdo == 1'b0 && field_backdoor_read("sw_b2bpdo") == 1'b1) 
      begin
         `uvm_info(get_type_name(), $sformatf("SW wrote 1 to b2b bit"), verbosity)   
         sw_bpdo = 1'b1; 
      end
      
      if (bpdo == 1'b1 && field_backdoor_read("sw_b2bpdo") == 1'b0)
      begin
         `uvm_info(get_type_name(), $sformatf("SW wrote 0 to b2b bit"), verbosity)   
         sw_bpdo = 1'b0; 
      end
   endtask // execute_external
    
   // ============================================
   //             read_context
   // ============================================   
   // After external command, SPU/MCU may ask HWS branch by writing 0x11 to hrr_hws_hrr_state
   // If this bit is "dirty" HWS have to fetch the next RDR according to ret context
   task read_context();
      net_rrt_sel  = field_backdoor_read("hrr_net_rrt_sel");

      // Reset "branch dirty bit" // TODO YS: not sur HWS does it here - ask YuvalA
      case (net_rrt_sel)
         RRT : 
         begin
            hws_ret_state = RRT_FETCH;
            rrt_rd_index = field_backdoor_read("hrr_rrt_rd_index");
         end
            
         NET : 
         begin
            hws_ret_state = NET_FETCH;
            net_rd_index = field_backdoor_read("hrr_net_rd_index");
         end
      endcase 
   endtask

   // ============================================
   //             power_down_seq
   // ============================================
   // After *NON B2B RDR* turn down all PDs
   // After *B2B RDR* turn down HW domains (currently only clb)
   // After *B2B RDR* FW domains kept on (if BPDO == 1 -> SW domains will be turn off during power up seq)
   task power_down_seq(); 

  
      just_got_out_of_halt = 0; // reset for next rdr
  
      // if no b2b -> turn off all PDs
      if ((b2bm == 0) 
          || 
         (field_backdoor_read("hrr_hws_hrr_state") == BRANCH) && ((field_backdoor_read("sw_b2ben") == 1'b0))) // after branch with no B2B (only implicit) turn off PDs
      //if (b2bm == 0)
      begin
         clbpd = 0;
         msspd = 0;
         isppd = 0;
      end
      else
      begin
         // If b2b keep HW Domains as is
         // keep SW domais (mss/isp) as is - will be turn off according to bpdo on following powerup seq
         clbpd = (clbpd || field_backdoor_read("pgen_clb"));

         msspd = (msspd || field_backdoor_read("pgen_mss"));
         isppd = (isppd || field_backdoor_read("pgen_isp"));

         // Pgen overide by FW
         if ((isppd_at_go == 1'b1) && (isppd_at_done == 1'b0)) isppd = 0; // if turn off by FW 
         if ((msspd_at_go == 1'b1) && (msspd_at_done == 1'b0)) msspd = 0; // if turn off by FW 
      end            
            
      `uvm_info(get_type_name(), $sformatf("b2b = 0x%0h, msspd = 0x%0h, isppd = 0x%0h, clbpd = 0x%0h", b2bm, msspd, isppd, clbpd), verbosity);
      `uvm_info(get_type_name(), $sformatf("BKDR sw_b2bpdo = 0x%0h, msspd = 0x%0h, isppd = 0x%0h, clbpd = 0x%0h", field_backdoor_read("sw_b2bpdo"),field_backdoor_read("pgen_mss"),field_backdoor_read("pgen_isp"),field_backdoor_read("pgen_clb")), verbosity);

      // TODO YS: check pgenb (not a must since at beginning of rdr pgenb is checked)  
      pgen_regs_checker(`__LINE__);
            
      // Save previous pgenb
      clbpd_prev = clbpd;
      msspd_prev = msspd;
      isppd_prev = isppd;
   endtask // power_down_seq

   // ============================================
   //             write_context
   // ============================================
   // stores HWS context to ret  
   task write_context(); 
      `uvm_info(get_type_name(), $sformatf("Writing context checker"), verbosity);
      
      fork
         // not context `RET_WRITE_CHECK(drr_pend_vstart,              pend_vstart);           
         // not context `RET_WRITE_CHECK(drr_vstart_count_timer_enb,   vstart_count_timer_enb);
         begin `REG_WRITE_CHECK(hws_hrr_net_rrt_sel,   hrr_net_rrt_sel,   net_rrt_sel);   end // 0-RRT; 1-NET 
         begin `REG_WRITE_CHECK(hws_hrr_hws_hrr_state, hrr_hws_hrr_state, hws_ret_state); end         
         begin `REG_WRITE_CHECK(hws_hrr_rrt_rd_cntr,   hrr_rrt_rd_cntr,   rrt_rd_cntr);   end       
         begin `REG_WRITE_CHECK(hws_hrr_rrt_rd_index,  hrr_rrt_rd_index,  rrt_rd_index);  end          
         begin `REG_WRITE_CHECK(hws_hrr_net_rd_index,  hrr_net_rd_index,  net_rd_index);  end  
      join_any
   endtask
   
   
    
   // ============================================
   //             set_pu_name()
   // ============================================
   task set_pu_name();    
      case (external_rdr_type)
         FLL_RDR:     pu_name = "FLL";          
         PGX_RDR:     pu_name = "PGX";
         FMU_RDR:     pu_name = "FMU";
         SEC_RDR:     pu_name = "SEC";   
         CPU_ROM_RDR: pu_name = "CPU ROM";
         SPU_ROM_RDR: pu_name = "SPU ROM";
         CPU_NVM_RDR: pu_name = "CPU NVM";         
         SPU_NVM_RDR: pu_name = "SPU NVM";
         default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))   
      endcase // rdr command header
   endtask
   
   
   // ============================================
   //             wait_for_go()
   // ============================================
   task wait_for_go();

      if (vif.cif_hws_fll_cmd_go !== 1'b0) `uvm_error(get_type_name(),$sformatf("cif_hws_fll_cmd_go is already high"))      
      if (vif.cif_hws_pgx_cmd_go !== 1'b0) `uvm_error(get_type_name(),$sformatf("cif_hws_pgx_cmd_go is already high"))
      if (vif.cif_hws_fmu_cmd_go !== 1'b0) `uvm_error(get_type_name(),$sformatf("cif_hws_fmu_cmd_go is already high"))
      if (vif.cif_hws_sec_cmd_go !== 1'b0) `uvm_error(get_type_name(),$sformatf("cif_hws_sec_cmd_go is already high")) 
      if (vif.cif_hws_mss_cmd_go !== 1'b0) `uvm_error(get_type_name(),$sformatf("cif_hws_mss_cmd_go is already high"))
      if (vif.cif_hws_spu_cmd_go !== 1'b0) `uvm_error(get_type_name(),$sformatf("cif_hws_spu_cmd_go is already high"))

      case (external_rdr_type)
         FLL_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_fll_cmd_go), go_timout, "GO")          
         PGX_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_pgx_cmd_go), go_timout, "GO")
         FMU_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_fmu_cmd_go), go_timout, "GO")
         SEC_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_sec_cmd_go), go_timout, "GO")  
         CPU_ROM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_mss_cmd_go), go_timout, "GO")
         SPU_ROM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_spu_cmd_go), go_timout, "GO")
         CPU_NVM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_mss_cmd_go), go_timout, "GO")        
         SPU_NVM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_hws_spu_cmd_go), go_timout, "GO")
         default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))   
      endcase // rdr command header
      
            
      // Check all relevant PDs are out of reset
      check_oorst();
      
   endtask
   // ============================================
   //             check_cif_cmd()
   // ============================================
   // Compare actual CIF command from interface to expected command from the external RDR
   function check_cif_cmd();
      case (external_rdr_type)
         FLL_RDR:     if (vif.cif_hws_clb_cmd !== pu_cmd)      `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_clb_cmd, pu_name, pu_cmd, rdr))       
         PGX_RDR:     if (vif.cif_hws_pgx_cmd !== pu_cmd)      `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_pgx_cmd, pu_name, pu_cmd, rdr)) 
         FMU_RDR:     if (vif.cif_hws_clb_cmd !== pu_cmd)      `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_clb_cmd, pu_name, pu_cmd, rdr)) 
         SEC_RDR:     if (vif.cif_hws_sec_cmd !== pu_cmd)      `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_sec_cmd, pu_name, pu_cmd, rdr)) 
         CPU_ROM_RDR: if (vif.cif_hws_mss_cmd !== cpu_rom_cmd) `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_mss_cmd, pu_name, cpu_rom_cmd, rdr))
         SPU_ROM_RDR: if (vif.cif_hws_spu_cmd !== spu_rom_cmd) `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_spu_cmd, pu_name, spu_rom_cmd, rdr))
         CPU_NVM_RDR: if (vif.cif_hws_mss_cmd !== cpu_nvm_cmd) `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_mss_cmd, pu_name, cpu_nvm_cmd, rdr))
         SPU_NVM_RDR: if (vif.cif_hws_spu_cmd !== spu_nvm_cmd) `uvm_error(get_type_name(), $sformatf("Command <0x%0h> for unit %s is not <0x%0h> as expected. (RDR = 0x%0h)", vif.cif_hws_spu_cmd, pu_name, spu_nvm_cmd, rdr))
         default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))   
      endcase // rdr command header    
   endfunction 
     
   // ============================================
   //             wait_for_done()
   // ============================================
   task wait_for_done();

      int expected_awdt_counter_val;

      `uvm_info(get_type_name(), $sformatf("Wait for done"), verbosity) 


      `BEGIN_FIRST_OF 
         // wait for cif_done
         begin
            case (external_rdr_type)
               FLL_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_fll_hws_cmd_done),    done_timout, "DONE")      
               PGX_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_pgx_hws_cmd_done),    done_timout, "DONE")
               FMU_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.cif_fmu_hws_cmd_done),    done_timout, "DONE")
               SEC_RDR:     `SIGNAL_WATCHDOG(@(posedge vif.sec_hwscmd_cif_sec_done), done_timout, "DONE")
               CPU_ROM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_mss_hws_cmd_done),    done_timout, "DONE")
               SPU_ROM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_spu_hws_cmd_done),    done_timout, "DONE")
               CPU_NVM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_mss_hws_cmd_done),    done_timout, "DONE")     
               SPU_NVM_RDR: `SIGNAL_WATCHDOG(@(posedge vif.cif_spu_hws_cmd_done),    done_timout, "DONE")
               default: `uvm_error(get_type_name(),$sformatf("RDR command header <0x%0h> is not defined ",rdr[14:12]))   
            endcase // rdr command header
            `uvm_info(get_type_name(), $sformatf("Got done"), verbosity) 
         end

         // wait for awdt (abort RDR)
         begin
            @(posedge vif.soft_awdt_expire);
            if (mailbox.test_goals.exists("soft_awdt")) mailbox.test_goals["soft_awdt"]--;


            `uvm_info(get_type_name(), $sformatf("RDR was aborted because of AWDT timeout"), UVM_LOW);

            // check awdt counter value


            if (vif.hrr_awdt_soft_th === 0) `uvm_error(get_type_name(), $sformatf("soft_awdt_expire rise while soft awdt is disabled"))
            else expected_awdt_counter_val = cfg.calc_soft_th();

            
            if (vif.hrr_awdt_soft_th != 0)
            begin
               if (vif.awdt_counter_val != expected_awdt_counter_val)
               begin
                  `uvm_error(get_type_name(), $sformatf("hrr_awdt_soft_th is %0d but awdt_counter_val <%0d> is not %0d as expected", vif.hrr_awdt_soft_th, vif.awdt_counter_val, expected_awdt_counter_val))
               end
            end
         end
      `END_FIRST_OF 
   endtask
 
   // ============================================
   //             field_backdoor_read()
   // ============================================
   // TODO YS: add compare to interface
   // TODO YS: also check interface have no X
   function bit[31:0] field_backdoor_read(string field_name);
      bit[31:0] reg_value;

      if (init_done == 0)
      begin
         //`uvm_error(get_type_name(), $sformatf("reading from HRR before init done"))
         return 0;
      end

      reg_value = cfg.top_rgu.hws_rgu.get_field_by_name(field_name).get_mirrored_value();
      return reg_value;
   endfunction
 
   // ============================================
   //       Field_backdoor_read_and_check()
   // ============================================
   // calls field_backdoor_read and then compare to expected value
   function field_backdoor_read_and_check(string field_name, bit [31:0] expected_value, int line);
      if (field_backdoor_read(field_name) != expected_value)
         `uvm_error(get_type_name(),$sformatf("Line %0d: Register %s value is <0x%0h> and not <0x%0h> as expected", line,  field_name, field_backdoor_read(field_name) ,expected_value));
   endfunction
  
   // ============================================
   //                Get_memories()
   // ============================================ 
   function get_memories();
      $cast(nvm,cfg.top_rgu.get_mem_by_name("nvm"));
      net_offset = nvm.vmem_offset["net"];
      
      $cast(rom,cfg.top_rgu.get_mem_by_name("rom"));
      rrt_offset = rom.vmem_offset["rrt"];

      $cast(dbg_ram,cfg.top_rgu.get_mem_by_name("gpram"));

   endfunction // get_memories
  
   // ============================================
   //              Power_up_sequence()
   // ============================================      
   task power_up_sequence();    


      /*** NEW ORDER IS: ISP -> MSS -> CLB ***/
      /*** NEW ORDER IS: ISP -> MSS -> CLB ***/
      /*** NEW ORDER IS: ISP -> MSS -> CLB ***/

  
      // Check power up sequence by order (if not already on since prev RDR (B2B))
      if (isppd == 1) if (((just_got_out_of_halt == 0) && (isppd_prev == 0)) || ((just_got_out_of_halt == 1) && (isppd_ooh == 0))) power_up_checker("isp");
      if (msspd == 1) if (((just_got_out_of_halt == 0) && (msspd_prev == 0)) || ((just_got_out_of_halt == 1) && (msspd_ooh == 0))) power_up_checker("mss");
      if (clbpd == 1) if (((just_got_out_of_halt == 0) && (clbpd_prev == 0)) || ((just_got_out_of_halt == 1) && (clbpd_ooh == 0))) power_up_checker("clb");
   endtask // Power_up_sequence();

   // ============================================
   //            check_oorst();
   // ============================================
   // @ "GO" verify all relevant PDs are out of reset
   // TODO YS: add more PDs (rom, nvm etc....)
   function check_oorst();
      string msg = $sformatf("pd is not out of reset before GO (RDR type = %s)", pu_name);
      if (msspd == 1 && vif.hws_mss_rstn !== 1'b1) `uvm_error(get_type_name(),$sformatf("mss %s", msg)) 
      if (isppd == 1 && vif.hws_isp_rstn !== 1'b1) `uvm_error(get_type_name(),$sformatf("isp %s", msg))  
      if (clbpd == 1 && vif.hws_clb_rstn !== 1'b1) `uvm_error(get_type_name(),$sformatf("clb %s", msg))  
   endfunction

   
   // ============================================
   //         pgen_regs_checker()
   // ============================================   
   // Before power up sequence, checking writing to pgen registers
   // TODO also rst regs
   task pgen_regs_checker(int line);

     bit hwsintctl_pgen_mss_wen_s = vif.hwsintctl_pgen_mss_wen;
     bit hwsintctl_pgen_isp_wen_s = vif.hwsintctl_pgen_isp_wen;
     bit hwsintctl_pgen_clb_wen_s = vif.hwsintctl_pgen_clb_wen;


      string err_str = " was not set before power sequence";
      
      `uvm_info(get_type_name(), $sformatf("pgen_regs_checker called from line %0d b2b = 0x%0h, msspd = 0x%0h, isppd = 0x%0h, clbpd = 0x%0h", line, b2bm, msspd, isppd, clbpd), verbosity);

      
      if (vif.du_hws_prctl_sel === 1'b1)
      begin
         `uvm_info(get_type_name(), $sformatf("pgen_regs_checker called from line %0d ABORTED since DU has control over power signals", line), verbosity);
         return;
      end

 
      fork
      
         // mss pgen
         begin
            `SIGNAL_WATCHDOG(wait(vif.hwsintctl_pgen_mss_wen === 1'b1 || hwsintctl_pgen_mss_wen_s === 1'b1), 2, {"hwsintctl_pgen_mss_wen",err_str});
            wen_counter["hwsintctl_pgen_mss"]++;
            #1
            if (vif.hwsintctl_pgen_mss_wdata !== msspd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_pgen_mss_wdata is 0x%0h and not 0x%0h as expected", vif.hwsintctl_pgen_mss_wdata, msspd))
            @(posedge vif.soc_clk)
            #1
            if (vif.hwsintctl_pgen_mss !== msspd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_pgen_mss is 0x%0h and not 0x%0h as expected", vif.hwsintctl_pgen_mss, msspd))
         end
         
         // mss rstn
         begin 
            `SIGNAL_WATCHDOG(wait(vif.hwsintctl_rsten_mss_wen === 1'b1), 2, {"hwsintctl_rsten_mss_wen",err_str});
            wen_counter["hwsintctl_rsten_mss"]++;
            #1
            if (vif.hwsintctl_rsten_mss_wdata !== msspd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_rsten_mss_wdata is 0x%0h and not 0x%0h as expected", vif.hwsintctl_rsten_mss_wdata, msspd))
            @(posedge vif.soc_clk)
            #1
            if (vif.hwsintctl_rsten_mss !== msspd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_rsten_mss is 0x%0h and not 0x%0h as expected", vif.hwsintctl_rsten_mss, msspd))
         end
         
         // isp pgen
         begin 
            `SIGNAL_WATCHDOG(wait (vif.hwsintctl_pgen_isp_wen === 1'b1 || hwsintctl_pgen_isp_wen_s === 1'b1), 2, {"hwsintctl_pgen_isp_wen",err_str});
            wen_counter["hwsintctl_pgen_isp"]++;
            #1         
            if (vif.hwsintctl_pgen_isp_wdata !== isppd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_pgen_isp_wdata is 0x%0h and not 0x%0h as expected", vif.hwsintctl_pgen_isp_wdata, isppd))
            @(posedge vif.soc_clk)
            #1   
            if (vif.hwsintctl_pgen_isp !== isppd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_pgen_isp is 0x%0h and not 0x%0h as expected", vif.hwsintctl_pgen_isp, isppd))
         end
         
         // isp rstn
         begin 
            `SIGNAL_WATCHDOG(wait (vif.hwsintctl_rsten_isp_wen === 1'b1), 2, {"hwsintctl_rsten_isp_wen",err_str});
            wen_counter["hwsintctl_rsten_isp"]++;
            #1
            if (vif.hwsintctl_rsten_isp_wdata !== isppd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_rsten_isp_wdata is 0x%0h and not 0x%0h as expected", vif.hwsintctl_rsten_isp_wdata, isppd))
            @(posedge vif.soc_clk)
            #1
            if (vif.hwsintctl_rsten_isp !== isppd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_rsten_isp is 0x%0h and not 0x%0h as expected", vif.hwsintctl_rsten_isp, isppd))
         end
         
         // clb pgen
         begin 
            `SIGNAL_WATCHDOG(wait(vif.hwsintctl_pgen_clb_wen === 1'b1 || hwsintctl_pgen_clb_wen_s === 1'b1), 2, {"hwsintctl_pgen_clb_wen",err_str});
            wen_counter["hwsintctl_pgen_clb"]++;
            #1
            if (vif.hwsintctl_pgen_clb_wdata !== clbpd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_pgen_clb_wdata is 0x%0h and not 0x%0h as expected", vif.hwsintctl_pgen_clb_wdata, clbpd))
            @(posedge vif.soc_clk)
            #1
            if (vif.hwsintctl_pgen_clb !== clbpd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_pgen_clb is 0x%0h and not 0x%0h as expected", vif.hwsintctl_pgen_clb, clbpd))
         end
         
         // clb rstn
         begin 
            `SIGNAL_WATCHDOG(wait(vif.hwsintctl_rsten_clb_wen === 1'b1), 2, {"hwsintctl_rsten_clb_wen",err_str});
            wen_counter["hwsintctl_rsten_clb"]++;
            #1
            if (vif.hwsintctl_rsten_clb_wdata !== clbpd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_rsten_clb_wdata is 0x%0h and not 0x%0h as expected", vif.hwsintctl_rsten_clb_wdata, clbpd))
            @(posedge vif.soc_clk)
            #1
            if (vif.hwsintctl_rsten_clb !== clbpd) 
               `uvm_error(get_type_name(),$sformatf("hwsintctl_rsten_clb is 0x%0h and not 0x%0h as expected", vif.hwsintctl_rsten_clb, clbpd))
         end
         
         
      join_none
   endtask
   
   
   // ============================================
   //         power_up_checker()
   // ============================================   
   task power_up_checker(string pd_name);
      string msg;
         
      
      //`uvm_info (get_type_name(),$sformatf("%s power_up_checker start",pd_name ),verbosity);                                                    
      // Check pu is not on before sequence
      msg = $sformatf("Power domain %s is on before power up sequence started (PU = %s)",pd_name, pu_name);
      // Skip checking if out of halt - pu can be on because of DU
      if (just_got_out_of_halt == 0)
      begin
      case (pd_name)
         "clb" : if (vif.hws_adb_clb_pgen !== 1'b0) `uvm_error(get_type_name(),msg)
         "mss" : if (vif.hws_adb_mss_pgen !== 1'b0) `uvm_error(get_type_name(),msg)
         "isp" : if (vif.hws_adb_isp_pgen !== 1'b0) `uvm_error(get_type_name(),msg)
         default: `uvm_error(get_type_name(),$sformatf("PD name %s is not defined" ,pd_name))   
      endcase
      end    
  
      // Check PD is on in maximum 3 cycles 
      msg = $sformatf("Power domain %s was not turn on (PU = %s)",pd_name, pu_name);
      case (pd_name)
         "clb" : `SIGNAL_WATCHDOG(wait(vif.hws_adb_clb_pgen === 1'b1), 3, msg)
         "mss" : `SIGNAL_WATCHDOG(wait(vif.hws_adb_mss_pgen === 1'b1), 3, msg)
         "isp" : `SIGNAL_WATCHDOG(wait(vif.hws_adb_isp_pgen === 1'b1), 3, msg)
         default: `uvm_error(get_type_name(),$sformatf("PD name %s is not defined" ,pd_name))   
      endcase

      // After power up, checking reset (but continue to power up next power domain  
      fork
         begin
            repeat (3)
            begin
               msg = $sformatf("Power domain %s is out of reset less than 3.5 soc_clk cycles after power on (PU = %s)",pd_name, pu_name);
               // Skip checking if out of halt - pu can be out of reset because of DU
               if (just_got_out_of_halt == 0)
               begin
               case (pd_name)
                  "clb" : if (vif.hws_clb_rstn !== 1'b0) `uvm_error(get_type_name(),msg)
                  "mss" : if (vif.hws_mss_rstn !== 1'b0) `uvm_error(get_type_name(),msg)
                  "isp" : if (vif.hws_isp_rstn !== 1'b0) `uvm_error(get_type_name(),msg)
                  default: `uvm_error(get_type_name(),$sformatf("PD name %s is not defined" ,pd_name))   
               endcase
               end

               @(posedge vif.soc_clk);
            end
            
            @(negedge vif.soc_clk);
            #1ns; // data stable

            
            msg = $sformatf("Power domain %s is still in reset after 3.5 soc_clk cycles after power on(PU = %s)",pd_name, pu_name);
            case (pd_name)
               "clb" : if (vif.hws_clb_rstn !== 1'b1) `uvm_error(get_type_name(),msg)
               "mss" : if (vif.hws_mss_rstn !== 1'b1) `uvm_error(get_type_name(),msg)
               "isp" : if (vif.hws_isp_rstn !== 1'b1) `uvm_error(get_type_name(),msg)
               default: `uvm_error(get_type_name(),$sformatf("PD name %s is not defined" ,pd_name))   
            endcase

         end
      join_none
      //`uvm_info (get_type_name(),$sformatf("%s power_up_checker wait",pd_name ),verbosity);                                                    
      
      // Wait (4 *(ret_power_on_pd_gap) + 1 ) soc_cloc cycles before turning on next PD
      repeat (4*(vif.hrr_power_on_pd_gap) + 1)
      begin
         // TODO YS :  if really want, can add checker for other PDs are off
         @(posedge vif.soc_clk);
      end
      //`uvm_info (get_type_name(),$sformatf("%s power_up_checker end",pd_name ),verbosity);                                                    

   endtask

   // ============================================
   //              pwrctl rm ()
   // ============================================  
   // Monitoring pwrctl TDR
   // Use: 
   // 1. Wait for HWS is NOT active (aka in reset or halt) 
   // 2. Take control on power and reset (aka du_hws_prctl_sel = 1'b1)
   // 3. Turn on/off PDs: MSS - 0, ISP - 1, CLB - 2 
   // 4. Return control on power and reset (aka du_hws_prctl_sel = 1'b0) 

   // pwrctl TDR -> pwrctl_update pulse @du_tap -> pgen_wen @hws

   // even while in halt, hws turn PDs with gap


   // TODO TODO TODO
   // This is a BUG - need to first turn off domains. not to keep it active during turning on other PDs (wasting power)
   // TODO TODO TODO



   task pwrctl_rm();


      forever
      begin
         @(posedge vif.du_hws_pgen_wen iff vif.du_hws_pgen_wen === 1'b1);

         // Flow checkers
         if (vif.du_hws_prctl_sel !== 1'b1)
         begin
            `uvm_error(get_type_name(),$sformatf("PWRCTL TDR without du_hws_prctl_sel = 1"))
         end
  
         // Flow checkers
         if (!((vif.du_hws_halt === 1'b1) || (vif.adb_hws_rstn === 1'b0)))
         begin
            `uvm_error(get_type_name(),$sformatf("PWRCTL TDR while HWS is not in halt or reset"))
         end

         // Sampeling on wen
         du_pgen = vif.du_hws_pgen_wdata;

         // isp is written first after 2 cycles
         repeat (2) @(posedge vif.soc_clk);
         #1ns; // prevent race
         if (vif.adb_hws_rstn === 1'b1)
         begin
            if (vif.hws_adb_isp_pgen !== du_pgen[`ISP_POS]) `uvm_error(get_type_name(),$sformatf("ISP PWRCTL was not written"))
         end

         // MSS is written 2nd
         if (du_pgen != 0)
         begin
            // gap is only AFTER turn on
            repeat (4*(vif.hrr_power_on_pd_gap) + 1) @(posedge vif.soc_clk);
         end
         else
         begin
            // no gap for turn off
            @(posedge vif.soc_clk);
         end
         #1ns; // prevent race
         if (vif.adb_hws_rstn === 1'b1)
         begin
            if (vif.hws_adb_mss_pgen !== du_pgen[`MSS_POS]) `uvm_error(get_type_name(),$sformatf("MSS PWRCTL was not written"))
         end
 
          
         // CLB is written 3rd
         if (du_pgen != 0)
         begin
            // gap is only AFTER turn on
            repeat (4*(vif.hrr_power_on_pd_gap) + 1) @(posedge vif.soc_clk);
         end
         else
         begin
            // no gap for turn off
            @(posedge vif.soc_clk);
         end
         #1ns; // prevent race
         if (vif.adb_hws_rstn === 1'b1)
         begin
            if (vif.hws_adb_clb_pgen !== du_pgen[`CLB_POS]) `uvm_error(get_type_name(),$sformatf("CLB PWRCTL was not written"))
         end
      end

   endtask // pwrctl rm

   // ============================================
   //              rstctl rm ()
   // ============================================  
   // Monitoring rstctl TDR
   // Use: 
   // 1. Wait for HWS is NOT active (aka in reset or halt) 
   // 2. Take control on power and reset (aka du_hws_prctl_sel = 1'b1)
   // 3. Turn on/off PDs: MSS - 0, ISP - 1, CLB - 2 
   // 4. Return control on power and reset (aka du_hws_prctl_sel = 1'b0) 

   // pwrctl TDR -> pwrctl_update pulse @du_tap -> reset_wen @hws

   task rstctl_rm();


      forever 
      begin
         @(posedge vif.du_hws_rstctl_wen iff vif.du_hws_rstctl_wen === 1'b1);

         // Flow checkers
         if (vif.du_hws_prctl_sel !== 1'b1)
         begin
            `uvm_error(get_type_name(),$sformatf("RSTCTL TDR without du_hws_prctl_sel = 1"))
         end
  
         // Flow checkers
         if (!((vif.du_hws_halt === 1'b1) || (vif.adb_hws_rstn === 1'b0)))
         begin
            `uvm_error(get_type_name(),$sformatf("RSTCTL TDR while HWS is not in halt or reset"))
         end

         // Sampeling on wen
         du_rst = vif.du_hws_rstctl_wdata;

         // Flow checkers   
         if ((du_rst[`MSS_POS] == 1'b1) && (du_pgen[`MSS_POS] != 1'b1)) `uvm_error(get_type_name(),$sformatf("Taking MSS oorst while it is off"))
         if ((du_rst[`ISP_POS] == 1'b1) && (du_pgen[`ISP_POS] != 1'b1)) `uvm_error(get_type_name(),$sformatf("Taking ISP oorst while it is off"))
         if ((du_rst[`CLB_POS] == 1'b1) && (du_pgen[`CLB_POS] != 1'b1)) `uvm_error(get_type_name(),$sformatf("Taking CLB oorst while it is off"))
    
         // 3.5 cycles after rstctl write PD need to be oorst (all PDS at the same time)
         repeat (6) @(posedge vif.soc_clk);
         #1ns; // prevent race
         if (vif.adb_hws_rstn === 1'b1)
         begin
            if (vif.hws_mss_rstn !== du_rst[0]) `uvm_error(get_type_name(),$sformatf("MSS RSTCTL was not written"))
            if (vif.hws_isp_rstn !== du_rst[1]) `uvm_error(get_type_name(),$sformatf("ISP RSTCTL was not written"))
            if (vif.hws_clb_rstn !== du_rst[2]) `uvm_error(get_type_name(),$sformatf("CLB RSTCTL was not written"))
         end
      end

   endtask // pwrctl rm


   // 1. Checking write to rgu on begining of active (curent)
   // 2. Checking write to HRR on end of active (sum of curent + prev)
   // 3. frc reset before poff is already checked - not checking it heare 
   task sys_time_checker();
      int exp_ret_cycles;
      `ifdef HWS_DBG vif.verif_sys_time_checker = 1'b1; `endif

         @(posedge vif.soc_clk);
         @(posedge vif.soc_clk);
         exp_ret_cycles = vif.adb_hws_frc_counter;
         @(negedge vif.soc_clk);
         
         ret_cycles = cfg.hws_rgu.get_field_by_name("current_value").get_mirrored_value(); 
         `uvm_info (get_type_name(),$sformatf("ret_cycles = %0d", ret_cycles), verbosity);
         `uvm_info (get_type_name(),$sformatf("adb_hws_frc_counter = %0d", vif.adb_hws_frc_counter), verbosity);
         `uvm_info (get_type_name(),$sformatf("prev_hrr_sys_time = %0d", prev_hrr_sys_time), verbosity);
         `uvm_info (get_type_name(),$sformatf("debug_mode = %0d", cfg.debug_mode), verbosity);
         if (ret_cycles != exp_ret_cycles)
         begin
            `uvm_error(get_type_name(),$sformatf("RGU sys_time/current_value (%0d) is not vif.adb_hws_frc_counter (%0d) as expected", ret_cycles, exp_ret_cycles))
         end
         `BEGIN_FIRST_OF
            @(negedge vif.adb_hws_rstn);
            @(negedge vif.hws_hrr_sys_time_wen);
            @(hard_awdt == 1);
         `END_FIRST_OF
         `uvm_info (get_type_name(),$sformatf("hard_awdt = 0x%0h",hard_awdt), verbosity);

         if (hard_awdt == 0)
         begin
            if (vif.adb_hws_rstn === 1'b0 && cfg.debug_mode == 0 && vif.hrr_wkup_mode != 2'b10) `uvm_error(get_type_name(),$sformatf("hrr_sys_time was not written"))
            if (vif.adb_hws_rstn === 1'b1)
            begin 
              //@(posedge vif.soc_clk);
              #390ns; // this is the max value of random delay inside hrr between wen amd data valid
              curr_hrr_sys_time = cfg.hws_rgu.get_field_by_name("hrr_sys_time").get_mirrored_value();
              `uvm_info (get_type_name(),$sformatf("curr_hrr_sys_time = %0d", curr_hrr_sys_time), verbosity);
              if (curr_hrr_sys_time != prev_hrr_sys_time + ret_cycles)
              begin
                 `uvm_error(get_type_name(),$sformatf("hrr_sys_time (%0d) != perv value (%0d) + ret_cycles (%0d)",curr_hrr_sys_time, prev_hrr_sys_time, ret_cycles))
              end
              prev_hrr_sys_time = curr_hrr_sys_time;
            end
            else
            begin
               `uvm_info (get_type_name(),$sformatf("skipped sys time check (hws_rstn negedge)"), verbosity);
            end  
         end
         else
         begin
            `uvm_info (get_type_name(),$sformatf("skipped sys time check (hard_awdt)"), verbosity);
         end        
      `ifdef HWS_DBG vif.verif_sys_time_checker = 1'b0; `endif
     
   endtask 


   task init_rm();
      @(negedge vif.drr1_shadow_hrr_init_not_done);
      `uvm_info(get_type_name(), $sformatf("init done - hrr values are now true and not zero"), verbosity); 
      init_done = 1'b1;
   endtask


   task soft_awdt_rm();

      int soft_th = 1000;
      expected_soft_awdt_counter_val = 0;
      `ifdef HWS_DBG vif.expected_soft_awdt_counter_val = expected_soft_awdt_counter_val; `endif


      `BEGIN_FIRST_OF
         begin
            forever
            begin
               @(posedge vif.hws_envdet_clk_sync iff (vif.rgu_clear_awdt_en === 1'b0));
               if ((vif.hrr_awdt_soft_th != 0))
               begin
                  if (vif.cif_hws_fll_cmd_go === 1'b1 || vif.cif_hws_pgx_cmd_go === 1'b1 || vif.cif_hws_fmu_cmd_go === 1'b1 || vif.cif_hws_sec_cmd_go === 1'b1)
                  begin
                     expected_soft_awdt_counter_val ++; 
                     soft_th = cfg.calc_soft_th();

                     `ifdef HWS_DBG vif.expected_soft_awdt_counter_val = expected_soft_awdt_counter_val; `endif
                     `ifdef HWS_DBG vif.soft_th = soft_th; `endif

                     if ((expected_soft_awdt_counter_val == soft_th) && (vif.hrr_awdt_soft_th != 0))
                     begin
                        fork 
                            begin 
                               `SIGNAL_WATCHDOG(@(posedge vif.soft_awdt_expire), 2, "soft_awdt_expire not rise"); 
                            end
                        join_none
                     end
                  end
               end
            end // clk forever
         end // clk thread

         // Reset on clear
         begin
            forever
            begin
               @(posedge vif.rgu_clear_awdt_en);
               expected_soft_awdt_counter_val = 0;
               `ifdef HWS_DBG vif.expected_soft_awdt_counter_val = expected_soft_awdt_counter_val; `endif
            end
         end // clear forever

         // Reset on HW go
         // TODO YS: maybe also on SW go????
         begin
            forever
            begin
               @(posedge vif.cif_hws_fll_cmd_go, posedge vif.cif_hws_pgx_cmd_go, posedge vif.cif_hws_fmu_cmd_go, posedge vif.cif_hws_sec_cmd_go);
               expected_soft_awdt_counter_val = 0;
               `ifdef HWS_DBG vif.expected_soft_awdt_counter_val = expected_soft_awdt_counter_val; `endif
            end
         end //HW go forever
         




         // exit on reset
         begin
            @(negedge vif.adb_hws_rstn);
            expected_soft_awdt_counter_val = 0;
            `ifdef HWS_DBG vif.expected_soft_awdt_counter_val = expected_soft_awdt_counter_val; `endif
         end

         

      `END_FIRST_OF
      //vif.release_clear_awdt(); // in case it was not released before since no clk
   endtask


   // ============================================
   //              predict hard counter value ()
   // ============================================  
   // 1. Predict hard counter value
   // 2. On timout -> check poff rise
   task hard_awdt_rm();

      int hard_th = 1000;
      set_hard_awdt(0);

      `uvm_info(get_type_name(), $sformatf("hard_awdt_rm start"), verbosity); 
      `BEGIN_FIRST_OF
         begin
            forever
            begin

               // Count on envdet clock
               @(posedge vif.hws_envdet_clk_sync iff ((vif.rgu_clear_awdt_en === 1'b0) && (vif.du_hws_halt === 1'b0)));
               if (vif.hrr_awdt_hard_th != 3)
               begin
                  expected_hard_awdt_counter_val ++; 
                  set_hard_awdt(expected_hard_awdt_counter_val);

                  case (vif.hrr_awdt_hard_th)
                     0: hard_th = 1023;
                     1: hard_th = 255;
                     2: hard_th = 511;                     
                     3: set_hard_awdt(0);
                  endcase
               end
              

               // On almost hard awdt event
               // `uvm_info(get_type_name(), $sformatf("expected_hard_awdt_counter_val = %0d, hard_th = %0d", expected_hard_awdt_counter_val, hard_th), verbosity);
               if (vif.hrr_awdt_hard_th !== 3)
               begin 
                  if (expected_hard_awdt_counter_val == hard_th-1)
                  begin
                     `uvm_info(get_type_name(), $sformatf("Almost hard_awdt - rise dig reset"), verbosity); 

                     fork `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_awdt_dig_reset), 2, "hws_adb_awdt_dig_reset not rise"); join_none
                  end

                  // On hard awdt event
                  if (expected_hard_awdt_counter_val == hard_th)
                  begin
                     `uvm_info(get_type_name(), $sformatf("hard_awdt - rise poff"), verbosity); 
                     hard_awdt = 1'b1;
                     fork `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_self_poff), 2, "hws_adb_self_poff not rise"); join_none
                  end
               end
            end
         end // clk forever


         begin
            @(posedge vif.hws_adb_awdt_dig_reset iff (vif.adb_hws_rstn===1'b1));
            `uvm_info(get_type_name(), $sformatf("hard_awdt - force from sw"), verbosity); 
            fork `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_awdt_dig_reset), 2, "hws_adb_awdt_dig_reset not rise"); join_none
            fork `SIGNAL_WATCHDOG(@(posedge vif.hws_adb_self_poff), 2, "hws_adb_self_poff not rise"); join_none
            hard_awdt = 1'b1;
         end

         begin
         @(negedge vif.adb_hws_rstn iff (vif.adb_hws_rstn===1'b0));
            `uvm_info(get_type_name(), $sformatf("hard_awdt - reset not awdt"), verbosity); 
         end

      `END_FIRST_OF
      set_hard_awdt(0);
      `uvm_info(get_type_name(), $sformatf("hard_awdt_rm end"), verbosity); 
   endtask

   function set_hard_awdt(int val);
      expected_hard_awdt_counter_val = val;
      `ifdef HWS_DBG vif.expected_hard_awdt_counter_val = expected_hard_awdt_counter_val; `endif
   endfunction

   // ============================================
   //              calc preset ()
   // ============================================  
   // calculate preset
   // for timer 1: just after rtcc the selected timer_index and then back to timer_index1  
   function bit [7:0] calc_preset();
      //TODO YS: comapre vif value to backdoor read
      bit [7:0] val;
      case (timer_index)
         0: val = (vif.hrr_timer0);
         1: val = ({vif.hrr_timer1,2'b0});
         2: val = ({vif.hrr_timer2_3,2'b0}); 
         3: val = ({vif.hrr_timer2_3,2'b0}); 
      endcase
       
      if (val == 0) `uvm_fatal(get_type_name(),$sformatf("Preset = 0. Please set hrr_timer register before using timers"));

      return val;
   endfunction
      
   // ============================================
   //              set preset ()
   // ============================================  
   // calculate preset
   // for timer 1: just after rtcc the selected timer_index and then back to timer_index0  
   function set_preset(bit [7:0] val, int line = 0);
      //TODO YS: comapre vif value to backdoor read
      preset = val;
       
 
      `ifdef HWS_DBG 
         vif.verif_preset = preset; 
         `uvm_info(get_type_name(), $sformatf("Preset was set to 0x%0h, index = %0d (line: %0d)", preset, timer_index, line), verbosity); 
      `endif 

   endfunction
     
   // ============================================
   //              read_hrr_regs
   // ============================================
   // Reads all HRR regs Backdoor
   // Can also read fields
   
   task read_hrr_regs(bit print = 0, bit fields = 0, print_fields = 0);
      hrr_registers.delete(); // reset array
      cfg.hws_rgu.HRR.get_registers(hrr_registers);
      foreach (hrr_registers[hrr_reg])
      begin
         temp_val = 32'hcafecafe; // initial value to detect wrong read
         register =  hrr_registers[hrr_reg];
         register.read(status, temp_val, UVM_BACKDOOR);
         if (print) `uvm_info (get_type_name(),$sformatf("reg %s = 0x%0h", register.get_name(), temp_val), UVM_MEDIUM);
         if (fields) read_hrr_reg_field();
         if (print_fields)`uvm_info (get_type_name(),$sformatf("*****"), UVM_MEDIUM);  
      end
   endtask

   // ============================================
   //              read_hrr_reg_field
   // ============================================
   // Reads all HRR regs fields Backdoor
   
   task read_hrr_reg_field(bit print = 0);
      reg_fields.delete();
      register.get_fields(reg_fields);
      foreach (reg_fields[reg_field])
      begin
         temp_val = 32'hcafecafe;
         reg_fields[reg_field].read(status, temp_val, UVM_BACKDOOR);
         if (print) `uvm_info (get_type_name(),$sformatf("field %s = 0x%0h (0x%0h) [0x%0h]",reg_fields[reg_field].get_name(), temp_val, reg_fields[reg_field].get_mirrored_value(), field_backdoor_read(reg_fields[reg_field].get_name())), UVM_MEDIUM);
      end
   endtask

   // ============================================
   //              aon_timer_checker
   // ============================================
   // 
   function aon_timer_checker();

      int timer_down = field_backdoor_read("aon_timer_value_down");
      int timer_up   = field_backdoor_read("aon_timer_value_up");

      int aon_preset  = mailbox.aon_timer_preset;
      int aon_clk_sel = mailbox.aon_timer_clk_sel;
      int aon_timer_locked_value = mailbox.aon_timer_locked_value;

      int exp_timer_down = (4 ** aon_clk_sel) *  aon_timer_locked_value;
      int exp_timer_up   = (4 ** aon_clk_sel) * (aon_preset - aon_timer_locked_value);


      if (aon_clk_sel == 99) // 99 is reset value and if it is not ovveriten aon_sb is not workung
      begin
         `uvm_info (get_type_name(),$sformatf("aon_sb is disabled skipping timer check"), verbosity);
         return;
      end

      `uvm_info (get_type_name(),$sformatf("timer_down <0x%0h>, timer_up <0x%0h>, aon_preset <0x%0h>, aon_clk_sel <0x%0h>, aon_timer_locked_value <0x%0h>, exp_timer_down <0x%0h>, exp_timer_up <0x%0h>", timer_down, timer_up, aon_preset, aon_clk_sel, aon_timer_locked_value, exp_timer_down, exp_timer_up), verbosity);

      if (timer_down != exp_timer_down) 
         `uvm_error(get_type_name(),$sformatf("aon_timer_value_down <0x%0h> != expected <0x%0h>", timer_down, exp_timer_down))

      if (timer_up != exp_timer_up) 
         `uvm_error(get_type_name(),$sformatf("aon_timer_value_up <0x%0h> != expected <0x%0h>", timer_up, exp_timer_up))

      if (mailbox.test_goals.exists("aon_timer_checker")) mailbox.test_goals["aon_timer_checker"]--;

   endfunction

   // ============================================
   //              wait_with_error
   // ============================================
   // gets a number of cycles and set an error after that amount of soc_clk cycles
   task wait_with_error(int cycles, string str);
      repeat (cycles) @(posedge vif.soc_clk);
      #1ns; // prevent race 
      case (str)
         "GO": `uvm_error(get_type_name(),$sformatf("HWS RDR <0x%0h> for unit %s but no cif go after %0d soc_clk cycles", rdr, pu_name, cycles))
         "DONE": `uvm_fatal(get_type_name(),$sformatf("HWS RDR <0x%0h> for unit %s but no cif done after %0d soc_clk cycles", rdr, pu_name, cycles))
         default: `uvm_error(get_type_name(),$sformatf("Condition for SIGNAL_WATCHDOG Macro wasn`t achived (%s)",str))   
      endcase
   endtask
   
   // ============================================
   //              macro_delay
   // ============================================
   // return after delay according to register name
   task macro_delay(string reg_name);

      `uvm_info (get_type_name(),$sformatf("macro delay for field %s", reg_name), verbosity)
      if (reg_name.substr(0,2) == "hrr")
      begin
         // internal RANDOM delay inside hrr 
         #400ns;     
      end
      else
      begin
         // drr update on posedge
         @(posedge vif.soc_clk);      
      end
   endtask

   // ============================================
   //              end_of_wave_checker
   // ============================================
   task end_of_wave_checker();
      fork // fork used as .start() - AKA makes this function run in parallel to the main process
         begin 
            forever
            begin
               @(posedge vif.hws_adb_self_poff);

               if (during_fetch_from_net == 1'b1) `uvm_error(get_type_name(),$sformatf("poff during fetch from net"))
               if (during_fetch_from_rrt == 1'b1) `uvm_error(get_type_name(),$sformatf("poff during fetch from rrt"))
               if (during_fetch_from_net_dbg_ram == 1'b1) `uvm_error(get_type_name(),$sformatf("poff during fetch from net_dbg_ram"))
               if (during_fetch_from_rrt_dbg_ram == 1'b1) `uvm_error(get_type_name(),$sformatf("poff during fetch from rrt_dbg_ram"))
               #1ns; 
            end
         end
      join_none
   endtask    // end_of_wave_checker  
   
   // ============================================
   //            Measure_soc_clock
   // ============================================
   task measure_soc_clock();
      time soc_cloc_time;
      fork 
         begin
            @(posedge vif.soc_clk);
            soc_cloc_time = $time;
            @(posedge vif.soc_clk);
            soc_cloc_time = $time - soc_cloc_time;
            `uvm_info("PWR_LOG", $sformatf("soc clk period = %t", soc_cloc_time), UVM_NONE) // power logging  
         end
      join_none  
   endtask

   // ============================================
   //           check_branch 
   // ============================================
   task check_branch();
      `uvm_info (get_type_name(),$sformatf("HWS status ret = 0x%0h, vif = 0x%0h", field_backdoor_read("hrr_hws_hrr_state"), vif.hrr_hws_hrr_state), verbosity);

      if (field_backdoor_read("hrr_hws_hrr_state") == BRANCH)
      begin
         b2bm = 1; // branch descriptor is execute b2b (implicit)
         rdr_type = INTERNAL; // branch descriptor is like internal 
         `uvm_info (get_type_name(),$sformatf("before branch net_rrt_sel = %s, rrt_rd_index = %0d, net_rd_index = %0d", net_rrt_sel.name(), rrt_rd_index, net_rd_index), verbosity);
         read_context();
         `uvm_info (get_type_name(),$sformatf("HWS branched to a new context: net_rrt_sel = %s, rrt_rd_index = %0d, net_rd_index = %0d", net_rrt_sel.name(), rrt_rd_index, net_rd_index), verbosity);
      end 


   endtask



   // ============================================
   //              wen mon
   // ============================================
   // Monitors HW writes to ret 
   // every write increase wen_arr 
   task wen_mon();
      fork // fork used as .start() - AKA makes this function run in parallel to the main process 
         begin
            fork // fork between signals
               forever @(posedge vif.du_hws_pgen_wen)                             wen_action("du_hws_pgen");
               forever @(posedge vif.du_hws_rstctl_wen)                           wen_action("du_hws_rstctl");
               forever @(posedge vif.drr0_shadow_vstart_count_timer_enb_wen)      wen_action("drr0_shadow_vstart_count_timer_enb");
               forever @(posedge vif.hws_hrr_hws_hrr_state_wen)                   wen_action("hrr_hws_hrr_state");
               forever @(posedge vif.hws_hrr_net_rd_index_wen)                    wen_action("hrr_net_rd_index");
               forever @(posedge vif.hws_hrr_rrt_rd_index_wen)                    wen_action("hrr_rrt_rd_index");
               forever @(posedge vif.hws_hrr_rrt_rd_cntr_wen)                     wen_action("hrr_rrt_rd_cntr");
               forever @(posedge vif.hws_hrr_net_rrt_sel_wen)                     wen_action("hrr_net_rrt_sel");
               forever @(posedge vif.drr1_shadow_pace_enb_wen)                    wen_action("drr1_shadow_pace_enb");
               forever @(posedge vif.hws_hrr_timer_except_en_wen)                 wen_action("hrr_timer_except_en");
               forever @(posedge vif.drr1_shadow_pend_vstart_wen)                 wen_action("drr1_shadow_pend_vstart");
               forever @(posedge vif.hwsintctl_pgen_mss_wen)                      wen_action("hwsintctl_pgen_mss");
               forever @(posedge vif.hwsintctl_pgen_isp_wen)                      wen_action("hwsintctl_pgen_isp");
               forever @(posedge vif.hwsintctl_pgen_clb_wen)                      wen_action("hwsintctl_pgen_clb");
               forever @(posedge vif.hwsintctl_rsten_mss_wen)                     wen_action("hwsintctl_rsten_mss");
               forever @(posedge vif.hwsintctl_rsten_isp_wen)                     wen_action("hwsintctl_rsten_isp");
               forever @(posedge vif.hwsintctl_rsten_clb_wen)                     wen_action("hwsintctl_rsten_clb");
               // softwear  forever @(posedge vif.rgu_sw_b2ben_wen)                            wen_action("rgu_sw_b2ben");
               // softwear  forever @(posedge vif.rgu_sw_b2bpdo_wen)                           wen_action("rgu_sw_b2bpdo");
               forever @(posedge vif.excphndlr_timer_exception_cause_status_wen)  wen_action("excphndlr_timer_exception_cause_status");
               forever @(posedge vif.excphndlr_nrgdet_exception_cause_status_wen) wen_action("excphndlr_nrgdet_exception_cause_status");
               forever @(posedge vif.excphndlr_awdt_exception_cause_status_wen)   wen_action("excphndlr_awdt_exception_cause_status");
         
            join_any
         end
      join_none
   endtask
   
   // ============================================
   //                wen_action()
   // ============================================   
   // function called after wen rise
   function wen_action(string field);
      //`uvm_info (get_type_name(),$sformatf("kaki++++++++++++ wen %s ^^^^^^^^^^^^", field),verbosity);
      wen_counter[field]--;
   endfunction
   
   // ============================================
   //                Reset()
   // ============================================      
   function reset_vars();  

 
      // reset all class vars
      enter_calls = 0; // in case of brownout we can not expect all calls to exit
      exit_calls = 0;  // in case of brownout we can not expect all calls to exit
     


      temp_val = 32'hcafecafe; // for reading registers 
      clbpd = 0;
      msspd = 0;
      isppd = 0;
      
      clbpd_prev = 0;
      msspd_prev = 0;
      isppd_prev = 0;

      dupd = 0; 


      exception_flag = 0; // Indicates exception occurre
      start_of_active_flag = 0; // Indicates HWS just got out of reset (used for exception detection)

      pend_vstart            = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
      vstart_count_timer_enb = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
      def_timer_enb          = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
      timer_except_en        = 1'b0; // implicit - not part of rtcc TODO YS: add logic for correct value
      pace_enb               = 1'b1; // implicit - not part of rtcc TODO YS: add logic for correct value
      preset           = 1'b0; // implicit - not part of rtcc TODO YS: add logic for correct value
 
      just_got_out_of_halt = 0;   
      
      
      timer_was_set_during_current_wave = 1'b0; // flat // TODO: YS: maybe also for SW timer not only RTCC
      check_timer = 1'b0; // flag to check timer values if timer was set on prvious wave

      during_fetch_from_net = 1'b0; // indicates fetch is active
      during_fetch_from_rrt = 1'b0; // indicates fetch is active
      during_fetch_from_net_dbg_ram = 1'b0; // indicates fetch is active
      during_fetch_from_rrt_dbg_ram = 1'b0; // indicates fetch is active


      prev_hrr_sys_time = 0;
/////////////////////////////////////////////////
      init_done = 0;
      
   endfunction // reset vars
 
   // ============================================
   //                Reset()
   // ============================================      
   virtual task reset_phase(uvm_phase phase);  

      `uvm_info(get_type_name(), $sformatf("%s_PHASE", phase.get_name().toupper()), verbosity)

      reset_vars();
   endtask // 

   // ============================================
   //                Main()
   // ============================================      
   virtual task main_phase(uvm_phase phase);  

      `uvm_info(get_type_name(), $sformatf("%s_PHASE", phase.get_name().toupper()), verbosity) 

      fork 
        collect_fcov();
      join_none
    
      if (cfg.sb_en == 1'b1) 
      begin

         `uvm_info (get_type_name(),$sformatf("HWS SB is runing"),UVM_MEDIUM)
         //wen_mon(); // run in parallel (monitors retention writes)
         end_of_wave_checker(); // run in parallel check no fetching while poff
         get_memories(); // maybe can be done in an earlier phase 
         run_between_brownouts(); 
      end
   endtask // Run
      
   // ============================================
   //                New()
   // ============================================
   function new(string name, uvm_component parent);
      super.new(name, parent);   
      cg__hws_rom_access = new();
      cg__hws_nvm_access = new();
   endfunction // new
 
   // ============================================
   //                build()
   // ============================================   
   function void build_phase(uvm_phase phase);
      super.build_phase(phase);
   endfunction // build_phase
    
   // ============================================
   //                Connect()
   // ============================================        
   function void connect_phase(uvm_phase phase);
      super.connect_phase(phase);  
      vif = cfg.vif;  

   endfunction // connect_phase

  
   // ============================================
   //                Shutdown()
   // ============================================     
   virtual task shutdown_phase (uvm_phase phase);
      super.shutdown_phase(phase);     
      //`uvm_info("CALLS", $sformatf("summery: enter = %0d, exit = %0d",  enter_calls, exit_calls), verbosity);  
      if (enter_calls != exit_calls) 
         `uvm_error(get_type_name(),$sformatf("enter <%0d> != exit <%0d>",  enter_calls, exit_calls))
   endtask // shutdown_phase
    
   // ============================================
   //                Check()
   // ============================================     
   virtual function void check_phase(uvm_phase phase);
      super.check_phase(phase);       
   endfunction // check_phase      

    ///////////////////////////////////////////////////////////////////////////////////////////////////////////
    // Functional coverage
    //  TODO: move this to a separate coverage class
    ///////////////////////////////////////////////////////////////////////////////////////////////////////////

    covergroup      cg__hws_rom_access;

        cp__hws_rom_func    :   coverpoint { vif.hws_rom_addr }
        {   // Bins taken from fw_code/sys/fw_e4_fsm/outputs/HWSList.list
            // Base address of HWS space in ROM is 'h4000_fc00
            // ROM HWS functions:
            bins HwsRomNetInit                                              = { [ ( ('h4000_fc00-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc00 - 'h4000_fc00 + 18 ) >> 1 ) - 1 ] };
            bins HwsRomFlowFSMPowerupB2B                                    = { [ ( ('h4000_fc12-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc12 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFlowManagerOverlayInitFromGnvm                       = { [ ( ('h4000_fc1a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc1a - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomTempSensingOverlayInitFromGnvm                       = { [ ( ('h4000_fc20-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc20 - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomRxSweepAndAuxMeasOverlayInitFromGnvm                 = { [ ( ('h4000_fc26-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc26 - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomTempSenseLvRadioInit                                 = { [ ( ('h4000_fc2c-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc2c - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomTempSenseLvActivation                                = { [ ( ('h4000_fc3a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc3a - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomTempSensePopulateOvlB2B                              = { [ ( ('h4000_fc42-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc42 - 'h4000_fc00 +  4 ) >> 1 ) - 1 ] };
            bins HwsRomRcSensConfigHwsAndRadio                              = { [ ( ('h4000_fc46-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc46 - 'h4000_fc00 + 12 ) >> 1 ) - 1 ] };
            bins HwsRomRcSensActivation                                     = { [ ( ('h4000_fc52-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc52 - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomRcSensPopulateOvlB2B                                 = { [ ( ('h4000_fc58-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc58 - 'h4000_fc00 +  4 ) >> 1 ) - 1 ] };
            bins HwsRomCleActivationForFllOperation                         = { [ ( ('h4000_fc5c-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc5c - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomCleActivationForWkupOperation                        = { [ ( ('h4000_fc6a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc6a - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomFsmDfMeasActivateB2B                                 = { [ ( ('h4000_fc78-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc78 - 'h4000_fc00 + 16 ) >> 1 ) - 1 ] };
            bins HwsRomFsmFmuLoDivSymConfigHwsAndRadio                      = { [ ( ('h4000_fc88-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc88 - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomFsmFmuLoDivSymVsSocActivateB2B                       = { [ ( ('h4000_fc96-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc96 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomEnvdetClkMeas                                        = { [ ( ('h4000_fc9e-'h4000_fc00) >> 1 ) : ( ( 'h4000_fc9e - 'h4000_fc00 + 12 ) >> 1 ) - 1 ] };
            bins HwsRomRtcClkMeas                                           = { [ ( ('h4000_fcaa-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcaa - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomSetAdbConfigForContWkup                              = { [ ( ('h4000_fcb4-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcb4 - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomRestoreAdbConfigAfterContWkup                        = { [ ( ('h4000_fcba-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcba - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomPreAuxMeasSequence                                   = { [ ( ('h4000_fcc0-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcc0 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomPostAuxMeasSequence                                  = { [ ( ('h4000_fcc8-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcc8 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomAuxMeasPopulateOvlB2B                                = { [ ( ('h4000_fcd2-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcd2 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomSymMeasPopulateOvlB2B                                = { [ ( ('h4000_fcdc-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcdc - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmAuxMeasRxConfigClbAndRadio                        = { [ ( ('h4000_fce4-'h4000_fc00) >> 1 ) : ( ( 'h4000_fce4 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmAuxMeasRxConfigClbAndRadioForContWkup             = { [ ( ('h4000_fcee-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcee - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmAuxMeasLoConfigClbAndRadio                        = { [ ( ('h4000_fcf8-'h4000_fc00) >> 1 ) : ( ( 'h4000_fcf8 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmSymMeasLoConfigClbAndRadio                        = { [ ( ('h4000_fd02-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd02 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmSymMeasLcConfigClbAndRadio                        = { [ ( ('h4000_fd0c-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd0c - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomFsmMeasLoVrefVbpCalibConfigClbAndRadio               = { [ ( ('h4000_fd1a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd1a - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmMeasLoVrefVbpCalibConfigClbAndRadioNoSampling     = { [ ( ('h4000_fd24-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd24 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmDfMeasConfigClbAndRadio                           = { [ ( ('h4000_fd2e-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd2e - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmFllMeasActivateB2B                                = { [ ( ('h4000_fd38-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd38 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmFllMeasActivateForContWkupB2B                     = { [ ( ('h4000_fd40-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd40 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomLoCalibPopulateOvlB2B                                = { [ ( ('h4000_fd4a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd4a - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmLoCalibConfigClbAndRadio                          = { [ ( ('h4000_fd52-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd52 - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmFllLoCalibActivateB2B                             = { [ ( ('h4000_fd5c-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd5c - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmLoCalibLvNoOtp                                    = { [ ( ('h4000_fd64-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd64 - 'h4000_fc00 + 18 ) >> 1 ) - 1 ] };
            bins HwsRomSymCalibPopulateOvlB2B                               = { [ ( ('h4000_fd76-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd76 - 'h4000_fc00 +  6 ) >> 1 ) - 1 ] };
            bins HwsRomFsmSymCalibConfigClbAndRadio                         = { [ ( ('h4000_fd7c-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd7c - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmFllSymCalibActivateB2B                            = { [ ( ('h4000_fd86-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd86 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomEncryptDataB2B                                       = { [ ( ('h4000_fd8e-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd8e - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxConfigHwsAndRadio                              = { [ ( ('h4000_fd98-'h4000_fc00) >> 1 ) : ( ( 'h4000_fd98 - 'h4000_fc00 + 12 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxLoDivSymConfigHwsAndRadio                      = { [ ( ('h4000_fda4-'h4000_fc00) >> 1 ) : ( ( 'h4000_fda4 - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxLoDivSymForBle5ConfigHwsAndRadio               = { [ ( ('h4000_fdb2-'h4000_fc00) >> 1 ) : ( ( 'h4000_fdb2 - 'h4000_fc00 + 20 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateMfgId                                  = { [ ( ('h4000_fdc6-'h4000_fc00) >> 1 ) : ( ( 'h4000_fdc6 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateSrvcId                                 = { [ ( ('h4000_fdce-'h4000_fc00) >> 1 ) : ( ( 'h4000_fdce - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateRawNonWhiteLegacy                      = { [ ( ('h4000_fdd6-'h4000_fc00) >> 1 ) : ( ( 'h4000_fdd6 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateAdvExtInd                              = { [ ( ('h4000_fdde-'h4000_fc00) >> 1 ) : ( ( 'h4000_fdde - 'h4000_fc00 + 10 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateAdvExtIndB2B                           = { [ ( ('h4000_fde8-'h4000_fc00) >> 1 ) : ( ( 'h4000_fde8 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateAuxAdvInd                              = { [ ( ('h4000_fdf0-'h4000_fc00) >> 1 ) : ( ( 'h4000_fdf0 - 'h4000_fc00 + 16 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateAuxAdvIndRaw                           = { [ ( ('h4000_fe00-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe00 - 'h4000_fc00 + 18 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateMfgIdNoOtp                             = { [ ( ('h4000_fe12-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe12 - 'h4000_fc00 + 18 ) >> 1 ) - 1 ] };
            bins HwsRomFsmPgxActivateSrvcIdNoOtp                            = { [ ( ('h4000_fe24-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe24 - 'h4000_fc00 + 18 ) >> 1 ) - 1 ] };
            bins HwsRomPreparePacketWithConstsB2B                           = { [ ( ('h4000_fe36-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe36 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomRadioTrngB2B                                         = { [ ( ('h4000_fe3e-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe3e - 'h4000_fc00 + 20 ) >> 1 ) - 1 ] };
            bins HwsRomRetWkupWithFreqOffset                                = { [ ( ('h4000_fe52-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe52 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomContWkupWithFreqOffset                               = { [ ( ('h4000_fe5a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe5a - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomRetWkupWithFreqOffsetWithException                   = { [ ( ('h4000_fe62-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe62 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomContWkupWithFreqOffsetWithException                  = { [ ( ('h4000_fe6a-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe6a - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins HwsRomLoProxSensingInit                                    = { [ ( ('h4000_fe72-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe72 - 'h4000_fc00 + 14 ) >> 1 ) - 1 ] };
            bins HwsRomLoProxSensingExecute                                 = { [ ( ('h4000_fe80-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe80 - 'h4000_fc00 + 20 ) >> 1 ) - 1 ] };
            bins HwsRomSymCalib                                             = { [ ( ('h4000_fe94-'h4000_fc00) >> 1 ) : ( ( 'h4000_fe94 - 'h4000_fc00 + 26 ) >> 1 ) - 1 ] };
            bins HwsRomPowerGearing                                         = { [ ( ('h4000_feae-'h4000_fc00) >> 1 ) : ( ( 'h4000_feae - 'h4000_fc00 + 24 ) >> 1 ) - 1 ] };
            bins PowerGearingExit                                           = { [ ( ('h4000_fec2-'h4000_fc00) >> 1 ) : ( ( 'h4000_fec2 - 'h4000_fc00 + 20 ) >> 1 ) - 1 ] };
            bins HwsRomLcAuxIdacCalibInit                                   = { [ ( ('h4000_fec6-'h4000_fc00) >> 1 ) : ( ( 'h4000_fec6 - 'h4000_fc00 + 12 ) >> 1 ) - 1 ] };
            bins HwsRomLcAuxIdacCalibExecute                                = { [ ( ('h4000_fed2-'h4000_fc00) >> 1 ) : ( ( 'h4000_fed2 - 'h4000_fc00 + 36 ) >> 1 ) - 1 ] };
            //bins LcAuxIdacCalibExecute                                      = { [ ( ('h4000_fed2-'h4000_fc00) >> 1 ) : ( ( 'h4000_fed2 - 'h4000_fc00 +  0 ) >> 1 ) - 1 ] };
            bins HwsRomPreHarvesterFlow                                     = { [ ( ('h4000_fef6-'h4000_fc00) >> 1 ) : ( ( 'h4000_fef6 - 'h4000_fc00 +  8 ) >> 1 ) - 1 ] };
            bins RAW_TX_LOOP                                                = { [ ( ('h4000_fefe-'h4000_fc00) >> 1 ) : ( ( 'h4000_fefe - 'h4000_fc00 + 44 ) >> 1 ) - 1 ] };
            bins repeat_tx_loop                                             = { [ ( ('h4000_ff0e-'h4000_fc00) >> 1 ) : ( ( 'h4000_ff0e - 'h4000_fc00 + 16 ) >> 1 ) - 1 ] };
            bins HarvesterTxStart                                           = { [ ( ('h4000_ff22-'h4000_fc00) >> 1 ) : ( ( 'h4000_ff22 - 'h4000_fc00 + 36 ) >> 1 ) - 1 ] };
            bins EndHarvFlow                                                = { [ ( ('h4000_ff28-'h4000_fc00) >> 1 ) : ( ( 'h4000_ff28 - 'h4000_fc00 + 42 ) >> 1 ) - 1 ] };

            bins NotHwsRomFunc                                              = default; 
        }

    endgroup    :   cg__hws_rom_access

    covergroup      cg__hws_nvm_access;

        cp__hws_nvm_func    :   coverpoint { vif.hws_nvm_addr }
        {   // Bins taken from fw_code/sys/fw_e4_fsm/outputs/HWSList.list
            // Base address of HWS space in NVM is 'h4001_0e00
            // NVM HWS functions:
            // TODO: use function lengths once they are corrected in HWSList.list
            bins StartOfHwsNvmSpace                                         = { [ ( ( 'h4001_0e00 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e08 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins FlowManagerFsm                                             = { [ ( ( 'h4001_0e08 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e38 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TempSensingLoop                                            = { [ ( ( 'h4001_0e38 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e40 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TempSensingLoopExecute                                     = { [ ( ( 'h4001_0e40 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e4a - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins LoProxSensingLoop                                          = { [ ( ( 'h4001_0e4a - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e54 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins RcSensorLoop                                               = { [ ( ( 'h4001_0e54 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e5c - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins RcSensorLoopExecute                                        = { [ ( ( 'h4001_0e5c - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e66 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TamperSensingLoop                                          = { [ ( ( 'h4001_0e66 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e6c - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins SystemClksMeasLoop                                         = { [ ( ( 'h4001_0e6c - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e70 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins SystemClksMeasExecute                                      = { [ ( ( 'h4001_0e70 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e78 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins SocMeasLoop                                                = { [ ( ( 'h4001_0e78 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e80 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins EnvdetMeasLoop                                             = { [ ( ( 'h4001_0e80 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e84 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins RtcMeasLoop                                                = { [ ( ( 'h4001_0e84 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e88 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins RxSweepAndAuxMeasLoop                                      = { [ ( ( 'h4001_0e88 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e90 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins AuxMeas                                                    = { [ ( ( 'h4001_0e90 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0e9a - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins AuxMeasExecute                                             = { [ ( ( 'h4001_0e9a - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ea2 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins PostAuxMeas                                                = { [ ( ( 'h4001_0ea2 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ea4 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins PostRxSweepAndAuxMeas                                      = { [ ( ( 'h4001_0ea4 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ea8 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins LoTxRxCalibLoop                                            = { [ ( ( 'h4001_0ea8 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0eae - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins LoTxRxCalibExecute                                         = { [ ( ( 'h4001_0eae - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0eba - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins SymCalibLoop                                               = { [ ( ( 'h4001_0eba - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ebe - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins SecAndTxLoop                                               = { [ ( ( 'h4001_0ebe - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ec8 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TxSprinkler                                                = { [ ( ( 'h4001_0ec8 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ed0 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins PreparePacketLoop                                          = { [ ( ( 'h4001_0ed0 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ee4 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TxLegacyLoop                                               = { [ ( ( 'h4001_0ee4 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0ef2 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TxBle5Loop                                                 = { [ ( ( 'h4001_0ef2 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f0e - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins TempStaticCompLoop                                         = { [ ( ( 'h4001_0f0e - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f14 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins PowerGearingLoop                                           = { [ ( ( 'h4001_0f14 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f18 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins LcAuxIdacCalibLoop                                         = { [ ( ( 'h4001_0f18 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f1e - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins WkupThresholdCalibLoop                                     = { [ ( ( 'h4001_0f1e - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f24 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins WkupLowSensitivityCalib                                    = { [ ( ( 'h4001_0f24 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f2e - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins LoVrefVbpCalibLoop                                         = { [ ( ( 'h4001_0f2e - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f38 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins LoVrefVbpCalibExecute                                      = { [ ( ( 'h4001_0f38 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f46 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins ModIdxCalibLoop                                            = { [ ( ( 'h4001_0f46 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f4c - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins ModIdxCalibExecute                                         = { [ ( ( 'h4001_0f4c - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f58 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins MiniRxLoop                                                 = { [ ( ( 'h4001_0f58 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f64 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins MiniRxMainLoop                                             = { [ ( ( 'h4001_0f64 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f66 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins NoContWuForFirstRun                                        = { [ ( ( 'h4001_0f66 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f76 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins ExitCheckRx                                                = { [ ( ( 'h4001_0f76 - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_0f7e - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };
            bins HarvesterFlow                                              = { [ ( ( 'h4001_0f7e - 'h4001_0e00 ) >> 1 ) : ( ( ( 'h4001_1000 - 'h4001_0e00 + 0 ) >> 1 ) - 1 ) ] };

            bins NotHwsNvmFunc                                              = default; 
        }

    endgroup    :   cg__hws_nvm_access

    task        collect_fcov();

        // TMP
        //cfg.functional_cov_en = 1;
        if ( cfg.functional_cov_en == 1 )
        begin
            `uvm_info( get_type_name(), "HWS functional coverage is enabled,  coverge will be collected during the test.    ", verbosity )

            fork
                begin   : rom_functions
                    forever @( vif.hws_rom_addr iff ( vif.hws_rom_sel && vif.adb_hws_rstn ) )
                    begin
                        `uvm_info( get_type_name(), $sformatf( "Sampling HWS functional coverage, sampled HWS ROM function address: [%0h]", vif.hws_rom_addr ), verbosity )
                        cg__hws_rom_access.sample();
                    end
                end     : rom_functions
                begin   : nvm_functions
                    forever @( posedge vif.soc_clk iff ( vif.adb_hws_rstn && vif.hws_nvm_pwron && vif.hws_nvm_sel && vif.nvm_hw_rdy && vif.nvm_hw_rdvld ) )
                    begin
                        `uvm_info( get_type_name(), $sformatf( "Sampling HWS functional coverage, sampled HWS NVM function address: [%0h]", vif.hws_nvm_addr ), verbosity )
                        cg__hws_nvm_access.sample();
                    end
                end     : nvm_functions
            join_none
        end
        else
            `uvm_info( get_type_name(), "HWS functional coverage is disabled, coverge will not be collected during the test.", verbosity )

    endtask :   collect_fcov

endclass    : pixie_hws_sb
    
