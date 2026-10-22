#!/usr/bin/env python3
"""Reproducible independent cross-survey ΛCDM consistency check (Planck 2018 vs DESI DR2 BAO)."""
from pathlib import Path
import json, datetime, hashlib, math
import numpy as np
from scipy.integrate import quad
from scipy.stats import chi2
ROOT=Path(__file__).resolve().parent
C_KM_S=299792.458
PLANCK={"H0_km_s_Mpc":67.4,"omega_m":0.315,"r_drag_Mpc":147.09,
"source":"https://doi.org/10.1051/0004-6361/201833910",
"parameter_origin":"Planck 2018 base LCDM, fixed illustrative parameter set, no DESI fit"}
values=[];zlist=[];kinds=[]
for line in (ROOT/"data/desi_dr2_mean.txt").read_text().splitlines():
    if not line or line.startswith("#"):continue
    z,value,kind=line.split()
    zlist.append(float(z));values.append(float(value));kinds.append(kind)
C=np.loadtxt(ROOT/"data/desi_dr2_cov.txt")
assert C.shape==(13,13) and len(values)==13
assert np.allclose(C,C.T,atol=1e-11) and np.all(np.linalg.eigvalsh(C)>0)
def E(z):return math.sqrt(PLANCK["omega_m"]*(1+z)**3+1-PLANCK["omega_m"])
def hdist(z):return C_KM_S/(PLANCK["H0_km_s_Mpc"]*E(z))
def mdist(z):return C_KM_S/PLANCK["H0_km_s_Mpc"]*quad(lambda x:1/E(x),0,z,epsabs=1e-11)[0]
def predict(z,k):
    dm=mdist(z); dh=hdist(z)
    if k=="DM_over_rs":return dm/PLANCK["r_drag_Mpc"]
    if k=="DH_over_rs":return dh/PLANCK["r_drag_Mpc"]
    if k=="DV_over_rs":return (z*dm*dm*dh)**(1/3)/PLANCK["r_drag_Mpc"]
    raise ValueError(k)
pred=[predict(z,k) for z,k in zip(zlist,kinds)]
d=np.array(values)-np.array(pred)
chisq=float(d@np.linalg.solve(C,d))
report={"title":"Fixed Planck 2018 ΛCDM predictions versus published DESI DR2 BAO measurements",
"method":"flat matter+Lambda late-time expansion; fixed Planck parameters, no fitting; full DESI covariance; no new physical law claim",
"planck":PLANCK,
"DESI_source":"https://github.com/CobayaSampler/bao_data/tree/master/desi_bao_dr2",
"measurement_count":13,"chi2":chisq,"reference_degrees_of_freedom":13,
"nominal_chi2_survival_p":float(chi2.sf(chisq,13)),
"caveat":"Nominal p ignores uncertainties and covariances in fixed Planck parameters and implementation simplifications. This is NOT a jointly fitted cosmology likelihood.",
"rows":[{"index":i,"z":z,"quantity":kind,"observed":value,"predicted_Planck_flat_LCDM":float(expected),
"observed_sigma":float(np.sqrt(C[i,i])),"residual":float(value-expected)} for i,(z,kind,value,expected) in enumerate(zip(zlist,kinds,values,pred))],
"computed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
out=ROOT/"output/planck_desi_comparison.json"
out.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"measurement_count":13,"chi2":round(chisq,4),"nominal_p":float(chi2.sf(chisq,13)),
"comparison_file":str(out),"sha256":hashlib.sha256(out.read_bytes()).hexdigest()},indent=2))
