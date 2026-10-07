const BD_BASE = "/system_super_administrator/blood-donor-management";

function esc(value){
    return String(value ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
}
function badge(value){
    const cls = String(value || "").toLowerCase().replace(/\s+/g,"-");
    return `<span class="badge ${cls}">${esc(value || "—")}</span>`;
}
function showMessage(text, type="success"){
    const el=document.getElementById("message");
    if(!el)return;
    el.className=`message show ${type}`;
    el.textContent=text;
    window.scrollTo({top:0,behavior:"smooth"});
}
async function api(path, options={}){
    const response=await fetch(BD_BASE+path, options);
    const data=await response.json().catch(()=>({ok:false,error:"Invalid server response."}));
    if(!response.ok || data.ok===false) throw new Error(data.error||"Request failed.");
    return data;
}
function jsonOptions(payload, method="POST"){
    return {method,headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)};
}
function queryString(form){return new URLSearchParams(new FormData(form)).toString()}
function confirmDelete(message){return window.confirm(message || "Delete this record?")}
