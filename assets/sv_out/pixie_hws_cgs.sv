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


