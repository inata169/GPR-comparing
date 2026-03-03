import sys
import traceback
from rtgamma.main import main

try:
    print("Starting wrapper...")
    args = [
        "--ref", "dicom/2024101700/RTDOSE_2.16.840.1.114337.1.6420.1764295957.1",
        "--eval", "dicom/2024101700/RTDOSE_2.16.840.1.114337.1.6420.1764295957.1",
        "--mode", "3d",
        "--opt-shift", "off",
        "--rtstruct", "dicom/2024101700/RTSTRUCT_2.16.840.1.114337.1.6420.1764295945.0",
        "--roi", "patient",
        "--report", "phits-linac-validation/output/rtgamma/struct_test_self"
    ]
    sys.argv[1:] = args
    main()
    print("Main finished successfully.")
except Exception as e:
    print("Exception caught in wrapper!")
    traceback.print_exc()
