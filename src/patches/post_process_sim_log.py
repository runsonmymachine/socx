"""
post proccesing run.log for errors/warning
input - log
parse log for errors - return pass or fail
fail - what failed (add aeon errors)
output - print to screen, log if failed
"""  # noqa: D400

import argparse
import os
import re  # regular expression


sim_ended_time_re = re.compile("finish at simulation time ([\\d]+)\\...ns")


class TestResults:
    def __init__(self):
        #        self.uvm_error = uvm_error
        self.ExceptionStr = ""
        self.ignoreListPath = os.path.join(
            os.environ["TOP_VERIF"], "sim_input", "socrunIgnoreList.txt"
        )
        self.ignToCheck = None
        self.init_ignore_list()
        self.vcs_compile_runtime = 0
        self.simv_runtime = 0
        self.reset_log(None)

    def reset_log(self, log_path, out_log_path=None):
        self.logPath = log_path
        self.outLogPath = out_log_path
        self.result = "NA"
        self.numErrors = 0
        self.simEnded = False
        self.simTime = 0
        self.errorList = []
        self.curr_iter = 0
        self.seed = 0

    def parse_log(self):
        """Parse the log."""
        if os.path.exists(self.logPath):
            #             status = 'PASS'
            self.result = "FAIL"
            self.simEnded = False

            # open file to see if simulation was ended

            with open(self.logPath) as f:
                log_dump = f.read()
                if re.search("--- UVM Report Summary ---", log_dump):
                    self.simEnded = True
                re_res = sim_ended_time_re.search(log_dump)
                if re_res is not None:
                    self.simTime = re_res.group(1)
                self.check_err(log_dump)
            if (self.numErrors == 0) & (self.simEnded):
                self.result = "PASS"
            if self.numErrors != len(self.errorList):
                print("Error: number of errors doesn't match error list.")

            # Print Log summary:
            if self.outLogPath is not None:
                with open(self.outLogPath, "w") as out_log:
                    if self.result == "PASS":
                        out_log.write("Test Pass\n")
                    else:
                        if self.numErrors > 0:
                            out_log.write(
                                "Those are the errors or warning that caused "
                                "the test to fail:\n"
                            )
                            for curr_err in self.errorList:
                                out_log.write(curr_err + "\n")
                            out_log.write(f"Total errors: {self.numErrors}\n")
                        out_log.write("Test failed\n")

                    if not self.simEnded:
                        out_log.write("Simulation didn't ended properly.")
                    else:
                        ratio = (float(self.simTime) / 1000000) / float(
                            self.simv_runtime
                        )
                        out_log.write(
                            f"Simulation ended after {self.simTime}ns."
                        )
                        out_log.write(
                            "Compilation run time: "
                            f"{self.vcs_compile_runtime}s\n"
                            "simulation run time: "
                            f"{self.simv_runtime}s \n"
                            "simulation time: "
                            f"{self.simTime} --> simulation time ratio: "
                            f"{ratio:5f}ms/s\n "
                        )

        else:
            err = f"log file doesnt exists {self.logPath}"
            raise ValueError(err)

    def check_err(self, line):
        """Check line if any ERROR pattern exists.

        The function will run for every line in log.

        Returns
        -------
        A string status, either 'ERROR' or 'IGNORE'.
        """
        # 'UVM_ERROR', - included in ERROR
        str_to_check = [
            "ERROR",
            "warning",
            "WARNING",
            "Error",
            "Fatal",
            "FATAL",
            "\\[NSC\\]Warning",
            "\\[NSC\\]Error",
            "\\*E",
            "\\*F",
        ]
        str_to_check_re = "(" + "|".join(str_to_check) + ")"
        str_to_check_re = f"\\n(.*{str_to_check_re}.*)\\n"
        targets = re.findall(str_to_check_re, line)
        for line, error_str in targets:
            if not self.ignore_err(line):
                self.errorList.append(line)
                self.numErrors += 1

    def init_ignore_list(self):
        self.ignToCheck = [
            "error_response_policy_enum",
            "UVM_ERROR :    0",
            "UVM_ERROR reports  :    0",
            "UVM_ERROR reports   :    0",
            "UVM_WARNING reports:    ",
            "UVM_WARNING reports :    ",
            "INFO = ",
            "\\[WARNING\\] \\[LP",
            "LP_MSG_SEV",
            "Number of demoted UVM_FATAL reports  :",
            "Number of demoted UVM_ERROR reports  :",
            "Number of demoted UVM_WARNING reports",
            "Number of caught UVM_FATAL reports   :    0",
            "Number of caught UVM_ERROR reports   :    0",
            "UVM_WARNING :    0",
            "UVM_FATAL :    0",
            "AEON\\/MTP EEPROM",
            "\\*Verdi\\* FSDB WARNING: The FSDB file already exists",
            "Warning-\\[LCA_FEATURES_ENABLED\\] Usage warning",
            "All future warnings not reported",
            "Total warnings:",
            "Verdi KDB elaboration finished with 0 error",
            "<<VIRL_MEM_WARNING:  No Operation as Memory is in Deep Sleep mode.>>",  # noqa: E501
            "Warning-\\[KDB-ELAB-W\\] Verdi KDB elaboration with warning",
        ]
        if os.path.exists(self.ignoreListPath):
            with open(self.ignoreListPath) as ignore_file:
                for line in ignore_file:
                    self.ignToCheck.append(line.strip())

    def ignore_err(self, line) -> bool:
        """Check line if any ignore pattern exists.

        The function will run for every line in log.
        """
        str_to_check_re = "(" + "|".join(self.ignToCheck) + ")"
        return bool(re.search(str_to_check_re, line))


def main():
    # getting the log from user
    parser = argparse.ArgumentParser(
        prog="ARGPARSER", description="Short sample app", add_help=False
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="the script help.",
    )
    parser.add_argument("-l", "--log", default=False, help="what is log")
    args = parser.parse_args()
    my_results = TestResults(args.log)
    my_results.parse_log()
    return my_results.result


if __name__ == "__main__":
    main()
