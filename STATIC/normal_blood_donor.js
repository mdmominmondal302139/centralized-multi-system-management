(() => {
"use strict";

const BASE = "/system_super_administrator/blood-donor-account";
const API = `${BASE}/api`;
const STATIC = "/system_super_administrator/blood-donor-management/static";
const state = { page: "home", account: null, profile: null };

const $ = (s, root=document) => root.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge = v => {
  const cls = String(v || "—").toLowerCase().replace(/\s+/g,"-");
  return `<span class="badge ${cls}">${esc(v || "—")}</span>`;
};
const fmtDateTime = v => {
  if (!v) return "—";
  const s=String(v).replace("T"," ");
  return s.length > 16 ? s.slice(0,16) : s;
};
function message(text, type="success") {
  const el=$("#message"); if(!el)return;
  el.className=`message show ${type}`;
  el.textContent=text;
  clearTimeout(message.timer);
  message.timer=setTimeout(()=>el.className="message",4500);
  window.scrollTo({top:0,behavior:"smooth"});
}
async function api(path, options={}) {
  const res=await fetch(API+path, options);
  const data=await res.json().catch(()=>({ok:false,error:"Invalid server response."}));
  if(!res.ok || data.ok===false) throw new Error(data.error || "Request failed.");
  return data;
}
const json = (body, method="POST") => ({
  method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(body)
});
function setActive(page){
  document.querySelectorAll(".nav a").forEach(a=>a.classList.toggle("active",a.dataset.page===page));
  document.querySelectorAll(".account-dropdown a[data-page]").forEach(a=>a.classList.toggle("active",a.dataset.page===page));
}
function updateHeader(title, subtitle){
  $("#pageTitle").textContent=title;
  $("#pageSubtitle").textContent=subtitle;
}
function donorOptions(selected=""){
  return ["A+","A-","B+","B-","AB+","AB-","O+","O-"].map(x=>`<option ${x===selected?"selected":""}>${x}</option>`).join("");
}
function shell(title, subtitle, body){
  updateHeader(title,subtitle);
  $("#workingArea").innerHTML=body;
}
async function loadHome(){
  shell("Home","Your donor information and eligibility overview.",`<div class="loading">Loading your donor information…</div>`);
  const d=await api("/home"); state.account=d.account;
  const donor=d.account.donor||{};
  $("#sideName").textContent=donor.full_name||"Blood Donor";
  $("#sideRole").textContent="Member";
  $("#topUser").textContent=donor.full_name||"Member";
  const eligibility=d.account.eligibility||"Unknown";
  $("#workingArea").innerHTML=`
    <section class="welcome-card">
      <div><span class="label">Welcome</span><h2>${esc(donor.full_name||"Blood Donor")}</h2><p>Your personal donor summary.</p></div>
      <div class="blood-mark">${esc(donor.blood_group||"—")}</div>
    </section>
    <div class="stat-grid">
      <div class="stat-card"><span>Blood Group</span><strong>${esc(donor.blood_group||"—")}</strong></div>
      <div class="stat-card"><span>Donor Status</span><strong>${badge(donor.donor_status||"Unknown")}</strong></div>
      <div class="stat-card"><span>Eligibility</span><strong>${badge(eligibility)}</strong></div>
      <div class="stat-card"><span>Total Donations</span><strong>${esc(d.account.total_donations||0)}</strong></div>
    </div>
    <div class="two-col">
      <section class="panel">
        <h3>Last Donation</h3>
        ${d.account.last_donation ? `<div class="detail-list"><div><span>Date</span><b>${esc(d.account.last_donation.donation_date||"—")}</b></div><div><span>Time</span><b>${esc(d.account.last_donation.donation_time||"—")}</b></div></div>` : `<div class="empty">No donation record found.</div>`}
      </section>
      <section class="panel">
        <h3>Next Eligible Donation</h3>
        <div class="detail-list"><div><span>Date</span><b>${esc(d.account.next_eligible_date||"—")}</b></div><div><span>Time</span><b>${esc(donor.next_eligible_time||"—")}</b></div></div>
      </section>
    </div>`;
}
async function loadRequestBlood(){
  shell("Request Blood","Find a matching donor first. Create a request only when a donor is not found.",`
    <section class="panel">
      <h2>Find Blood Donor</h2>
      <form id="findDonorForm" class="form-grid">
        <label>Blood Group<select name="blood_group" required><option value="">Select</option>${donorOptions()}</select></label>
        <label>District<select name="district"><option value="">Select</option><option>Rangpur</option><option>Dhaka</option><option>Rajshahi</option><option>Chattogram</option><option>Khulna</option><option>Barishal</option><option>Sylhet</option><option>Mymensingh</option></select></label>
        <label>Area<input name="area" placeholder="Area / locality"></label>
        <div class="form-actions"><button class="btn btn-primary" type="submit">🔍 Find Donor</button></div>
      </form>
    </section>
    <section id="donorResults"></section>
    <section id="requestCreate" class="panel hidden">
      <h2>Create Blood Request</h2>
      <p class="hint">No matching donor was found. You can now submit a blood request.</p>
      <form id="requestForm" class="form-grid">
        <label>Blood Group<select name="required_blood_group" id="requestBloodGroup" required><option value="">Select</option>${donorOptions()}</select></label>
        <label>Required Units<input name="quantity" type="number" min="1" step="1" required></label>
        <label>Required Date<input name="required_date" type="date" required></label>
        <label>Required Time<input name="required_time" type="time" required></label>
        <label class="wide">Hospital / Location<input name="hospital_name" required placeholder="Hospital / location"></label>
        <label class="wide">Additional Note<textarea name="notes" placeholder="Additional information"></textarea></label>
        <div class="form-actions wide"><button class="btn btn-save" type="submit">Submit Blood Request</button></div>
      </form>
    </section>`);
  $("#findDonorForm").addEventListener("submit", async e=>{
    e.preventDefault();
    const q=new URLSearchParams(new FormData(e.target));
    try{
      const d=await api(`/donors/search?${q}`);
      const box=$("#donorResults");
      if(!d.donors.length){
        box.innerHTML=`<section class="notice">No matching donor found.</section>`;
        $("#requestCreate").classList.remove("hidden");
        $("#requestBloodGroup").value=q.get("blood_group")||"";
        return;
      }
      $("#requestCreate").classList.add("hidden");
      box.innerHTML=`<section class="panel"><h2>Matching Donors</h2><div class="donor-grid">${
        d.donors.map(x=>`<article class="donor-card"><div class="donor-avatar">🩸</div><div><h3>${esc(x.full_name)}</h3><p><b>${esc(x.blood_group)}</b> · ${esc(x.district||"")}</p><span>${badge("Available")}</span></div><button class="btn btn-light donor-detail" data-id="${esc(x.donor_id)}">View Details</button></article>`).join("")
      }</div></section>`;
      box.querySelectorAll(".donor-detail").forEach(b=>b.addEventListener("click",()=>showDonorDetail(b.dataset.id)));
    }catch(err){message(err.message,"error")}
  });
  $("#requestForm").addEventListener("submit",async e=>{
    e.preventDefault();
    const f=new FormData(e.target), date=f.get("required_date"), time=f.get("required_time");
    const body={required_blood_group:f.get("required_blood_group"),quantity:f.get("quantity"),required_datetime:`${date}T${time}`,hospital_name:f.get("hospital_name"),notes:f.get("notes")};
    try{const d=await api("/request/create",json(body)); message(`Blood Request Submitted Successfully — Request ID: ${d.request.request_id}`); e.target.reset(); $("#requestBloodGroup").value=body.required_blood_group;}
    catch(err){message(err.message,"error")}
  });
}
async function showDonorDetail(id){
  try{
    const d=await api(`/donor/${encodeURIComponent(id)}`);
    const x=d.donor;
    const box=$("#donorResults");
    box.innerHTML=`<section class="panel detail-panel"><div class="panel-head"><h2>Donor Details</h2><button class="btn btn-light" id="backDonors">Back</button></div>
      <div class="detail-grid"><div><span>Name</span><b>${esc(x.full_name)}</b></div><div><span>Blood Group</span><b>${esc(x.blood_group)}</b></div><div><span>District</span><b>${esc(x.district||"—")}</b></div><div><span>Area</span><b>${esc(x.area||"—")}</b></div><div><span>Status</span>${badge(x.availability_status)}</div></div>
      <div class="notice">Contact details are not exposed in the public donor search. Use the existing communication/request workflow for contact.</div></section>`;
    $("#backDonors").addEventListener("click",loadRequestBlood);
  }catch(err){message(err.message,"error")}
}
async function loadRequests(){
  shell("View Requests","See active blood requests and respond only through the existing donor-match workflow.",`
    <section class="panel">
      <form id="requestSearch" class="search-grid">
        <input name="q" placeholder="Search request, blood group, hospital or ID">
        <select name="blood_group"><option value="">All Blood Groups</option>${donorOptions()}</select>
        <input name="location" placeholder="Location">
        <select name="status"><option value="">All Status</option><option>Pending</option><option>Searching Donor</option><option>Donor Found</option></select>
        <button class="btn btn-primary">Search</button>
      </form>
    </section>
    <section id="requestList"></section>`);
  const form=$("#requestSearch");
  async function fetchRows(){
    const q=new URLSearchParams(new FormData(form));
    try{
      const d=await api(`/requests?${q}`);
      $("#requestList").innerHTML=d.requests.length ? `<section class="panel table-wrap"><table><thead><tr><th>Request</th><th>Blood</th><th>Units</th><th>Location</th><th>Required</th><th>Urgency</th><th>Status</th><th></th></tr></thead><tbody>${
        d.requests.map(r=>`<tr><td>${esc(r.request_id)}</td><td><b>${esc(r.required_blood_group)}</b></td><td>${esc(r.quantity)}</td><td>${esc(r.hospital_name)}<small>${esc(r.location)}</small></td><td>${esc(fmtDateTime(r.required_datetime))}</td><td>${badge(r.urgency)}</td><td>${badge(r.status)}</td><td><button class="btn btn-light view-request" data-id="${esc(r.request_id)}">View Details</button></td></tr>`).join("")
      }</tbody></table></section>`:`<section class="panel empty">No active blood requests found.</section>`;
      $("#requestList").querySelectorAll(".view-request").forEach(b=>b.addEventListener("click",()=>showRequestDetail(b.dataset.id)));
    }catch(err){message(err.message,"error")}
  }
  form.addEventListener("submit",e=>{e.preventDefault();fetchRows()}); fetchRows();
}
async function showRequestDetail(id){
  try{
    const d=await api(`/request/${encodeURIComponent(id)}`);
    const r=d.request;
    $("#requestList").innerHTML=`<section class="panel"><div class="panel-head"><h2>Blood Request Details</h2><button class="btn btn-light" id="backRequests">Back</button></div>
      <div class="detail-grid"><div><span>Blood Group</span><b>${esc(r.required_blood_group)}</b></div><div><span>Required Units</span><b>${esc(r.quantity)}</b></div><div><span>Location</span><b>${esc(r.hospital_name)} ${esc(r.location)}</b></div><div><span>Required</span><b>${esc(fmtDateTime(r.required_datetime))}</b></div><div><span>Urgency</span>${badge(r.urgency)}</div><div><span>Status</span>${badge(r.status)}</div></div>
      ${r.matches?.length ? `<h3>Matching Donors</h3><div class="match-list">${r.matches.map(m=>`<div class="match-row"><div><b>${esc(m.donor_name)}</b><span>${esc(m.blood_group)} · ${esc(m.district||"")}</span></div>${badge(m.status)}${m.status==="Suggested"||m.status==="Contacted"?`<button class="btn btn-save accept-match" data-id="${esc(m.match_id)}">Accept</button>`:""}</div>`).join("")}</div>`:`<div class="notice">No donor match has been generated yet.</div><button class="btn btn-primary" id="findMatches">Find Matching Donors</button>`}
      <div class="private-note">Requester/patient private contact information is shown only to the request owner.</div>
      ${r.is_owner?`<div class="owner-box"><b>Your request</b><p>Requester: ${esc(r.requester_name||"—")} · Patient: ${esc(r.patient_name||"—")}</p></div>`:""}</section>`;
    $("#backRequests").addEventListener("click",loadRequests);
    const fm=$("#findMatches"); if(fm)fm.addEventListener("click",async()=>{try{await api(`/request/${encodeURIComponent(id)}/find-donors`,{method:"POST"});message("Matching donors searched successfully.");showRequestDetail(id)}catch(err){message(err.message,"error")}});
    $("#requestList").querySelectorAll(".accept-match").forEach(b=>b.addEventListener("click",async()=>{try{await api(`/match/${encodeURIComponent(b.dataset.id)}/accept`,{method:"POST"});message("Blood request accepted.");showRequestDetail(id)}catch(err){message(err.message,"error")}}));
  }catch(err){message(err.message,"error")}
}
async function loadRecords(){
  shell("Records","Your donation history and your own blood request history.",`<div class="loading">Loading records…</div>`);
  const d=await api("/records");
  $("#workingArea").innerHTML=`<section class="panel"><h2>Donation History</h2>${d.records.donations.length?`<div class="table-wrap"><table><thead><tr><th>Date</th><th>Time</th><th>Blood Group</th><th>Status</th></tr></thead><tbody>${d.records.donations.map(x=>`<tr><td>${esc(x.donation_date||"—")}</td><td>${esc(x.donation_time||"—")}</td><td>${esc(x.blood_group||"—")}</td><td>${badge(x.collection_status||x.screening_status||"Completed")}</td></tr>`).join("")}</tbody></table></div>`:`<div class="empty">No donation history found.</div>`}</section>
  <section class="panel"><h2>My Blood Requests</h2>${d.records.requests.length?`<div class="table-wrap"><table><thead><tr><th>Request ID</th><th>Blood Group</th><th>Date</th><th>Status</th></tr></thead><tbody>${d.records.requests.map(x=>`<tr><td>${esc(x.request_id)}</td><td>${esc(x.required_blood_group)}</td><td>${esc(fmtDateTime(x.created_at))}</td><td>${badge(x.status)}</td></tr>`).join("")}</tbody></table></div>`:`<div class="empty">No blood request history found.</div>`}</section>`;
}
async function loadProfile(){
  shell("Profile","Manage only the personal fields allowed for your donor account.",`<div class="loading">Loading profile…</div>`);
  const d=await api("/profile"); state.profile=d.profile||{};
  if(!state.profile){$("#workingArea").innerHTML=`<section class="panel empty">Your donor profile could not be found.</section>`;return;}
  const p=state.profile;
  $("#workingArea").innerHTML=`<section class="panel"><form id="profileForm" class="form-grid">
    <label>Full Name<input name="full_name" value="${esc(p.full_name)}"></label>
    <label>Mobile<input name="phone" value="${esc(p.phone)}"></label>
    <label>Email<input name="email" value="${esc(p.email)}"></label>
    <label>Blood Group<input value="${esc(p.blood_group)}" disabled></label>
    <label>District<input name="district" value="${esc(p.district)}"></label>
    <label>Area<input name="area" value="${esc(p.area)}"></label>
    <label>Upazila<input name="upazila" value="${esc(p.upazila)}"></label>
    <label>Account Status<input value="${esc(p.donor_status)}" disabled></label>
    <label class="wide">Address<textarea name="address">${esc(p.address)}</textarea></label>
    <label>Emergency Contact<input name="emergency_contact" value="${esc(p.emergency_contact)}"></label>
    <div class="form-actions wide"><button class="btn btn-update" type="submit">Update Profile</button></div>
  </form></section>`;
  $("#profileForm").addEventListener("submit",async e=>{e.preventDefault();try{const body=Object.fromEntries(new FormData(e.target));const x=await api("/profile/update",json(body));state.profile=x.profile;message("Profile updated successfully.");loadProfile()}catch(err){message(err.message,"error")}});
}
async function navigate(page, push=true){
  state.page=page;
  setActive(page);
  try{
    if(page==="home")await loadHome();
    else if(page==="request-blood")await loadRequestBlood();
    else if(page==="view-requests")await loadRequests();
    else if(page==="records")await loadRecords();
    else if(page==="profile")await loadProfile();
  }catch(err){$("#workingArea").innerHTML=`<section class="panel error-panel">${esc(err.message)}</section>`;message(err.message,"error")}
  if(push) history.pushState({page}, "", `${BASE}/${page}`);
}
document.addEventListener("click",e=>{
  const link=e.target.closest("a[data-page]");
  if(link){e.preventDefault();navigate(link.dataset.page);}
});
window.addEventListener("popstate",()=>navigate((location.pathname.split("/").pop()||"home"),false));
$("#accountToggle").addEventListener("click",()=>$("#accountDropdown").classList.toggle("show"));
document.addEventListener("click",e=>{if(!e.target.closest("#accountMenu"))$("#accountDropdown").classList.remove("show")});
const initial = location.pathname.split("/").pop();
navigate(["home","request-blood","view-requests","records","profile"].includes(initial)?initial:"home",false);
})();