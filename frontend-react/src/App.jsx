import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { BookOpen, Activity, FileText, Settings, UserPlus, Users, MessageSquare, Play, Square, RotateCcw, TrendingUp, Mic, Edit3, Trash2, BookText, GraduationCap, PlusCircle, Bot, Headphones, FilePlus, ChevronDown, ChevronUp, Save, BarChart3, AlertCircle, LogOut } from 'lucide-react';
import Login from './Login';

const API = import.meta.env.VITE_API_BASE || (window.location.hostname === "localhost" && window.location.port === "5173" ? "http://localhost:8000" : window.location.origin);
const authFetch = (url, options = {}) => {
  const token = localStorage.getItem("vachanam_token");
  const headers = { ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
};
const WS_URL = import.meta.env.VITE_WS_BASE || (window.location.hostname === "localhost" && window.location.port === "5173" ? "ws://localhost:8000/reading/ws/transcribe" : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/reading/ws/transcribe`);

const fmt = (s) => { const m = String(Math.floor(s/60)).padStart(2,"0"); const r = String(s%60).padStart(2,"0"); return `${m}:${r}`; };
const norm = (t) => (t||"").toLowerCase().replace(/[^\p{L}\p{N}\s]+/gu," ").replace(/\s+/g," ").trim();
const b64 = (i16) => { const b=new Uint8Array(i16.buffer); let s=""; for(let i=0;i<b.length;i+=0x8000) s+=String.fromCharCode(...b.slice(i,i+0x8000)); return btoa(s); };
const merge16 = (chunks) => { const t=chunks.reduce((s,c)=>s+c.length,0); const m=new Int16Array(t); let o=0; for(const c of chunks){m.set(c,o);o+=c.length;} return m; };

const cleanW = (w) => (w||"").toLowerCase().replace(/[^\p{L}\p{N}]/gu,"").replace(/[\u0901\u0902\u0903\u093C\u094D]/g,"");
const lev = (a,b) => { const m=a.length,n=b.length; if(!m) return n; if(!n) return m; let p=Array.from({length:n+1},(_,j)=>j); for(let i=1;i<=m;i++){const c=[i];for(let j=1;j<=n;j++) c[j]=a[i-1]===b[j-1]?p[j-1]:1+Math.min(p[j],c[j-1],p[j-1]); p=c;} return p[n]; };
const fuzzy = (a,b,thresh=0.35) => {
  const x=cleanW(a),y=cleanW(b); if(!x||!y) return false; if(x===y) return true;
  // Prefix/suffix match (Hindi matras often truncated)
  if(x.length>=3&&y.length>=3&&(x.startsWith(y)||y.startsWith(x)||x.endsWith(y)||y.endsWith(x))) return true;
  // Substring containment for short STT fragments
  if(x.length>=4&&y.length>=2&&x.includes(y)) return true;
  if(y.length>=4&&x.length>=2&&y.includes(x)) return true;
  const ml=Math.max(x.length,y.length); if(ml<=2) return x===y;
  return (1-lev(x,y)/ml)>=thresh;
};
const LOOK=5; // look-ahead window for skipping
const alignW = (exp,spk) => { const st=new Array(exp.length).fill("unread"); let ei=0,si=0; while(ei<exp.length&&si<spk.length){if(fuzzy(exp[ei],spk[si])){st[ei]="correct";ei++;si++;continue;}let skip=false;for(let k=1;k<=LOOK&&ei+k<exp.length;k++){if(fuzzy(exp[ei+k],spk[si])){for(let j=ei;j<ei+k;j++)st[j]="wrong";ei+=k;skip=true;break;}}if(skip)continue;for(let k=1;k<=LOOK&&si+k<spk.length;k++){if(fuzzy(exp[ei],spk[si+k])){si+=k;skip=true;break;}}if(skip)continue;st[ei]="wrong";ei++;si++;} return{statuses:st,reachedIndex:ei}; };
const langCode = (l) => { const s=(l||"").toLowerCase(); if(s.includes("hindi")||s==="hi") return "hi-IN"; if(s.includes("english")||s==="en") return "en-IN"; return "en-US"; };

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("vachanam_token") || null);
  const [user, setUser] = useState(JSON.parse(localStorage.getItem("vachanam_user")) || null);
  const [profileName, setProfileName] = useState("");
  const [profileSubject, setProfileSubject] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [students,setStudents]=useState([]); const [materials,setMaterials]=useState([]); const [teachers,setTeachers]=useState([]);
  const [selStudent,setSelStudent]=useState(""); const [selMaterial,setSelMaterial]=useState(""); const [selTeacher,setSelTeacher]=useState("");
  const [metrics,setMetrics]=useState(null); const [active,setActive]=useState(false);
  const [timeLeft,setTimeLeft]=useState(180); const [wsStatus,setWsStatus]=useState("idle"); const [error,setError]=useState("");
  const [expWords,setExpWords]=useState([]); const [wStatus,setWStatus]=useState([]); const [curIdx,setCurIdx]=useState(0);
  const [sessionId,setSessionId]=useState(null); const [evaluating,setEvaluating]=useState(false);
  const [manageTab,setManageTab]=useState("student"); // "teacher" | "student" | "material"
  const [pageTab,setPageTab]=useState("reading"); // "reading" | "history" | "management" | "reports"
  const [history,setHistory]=useState([]); const [histLoading,setHistLoading]=useState(false);
  const [expandedSession,setExpandedSession]=useState(null);

  // ── Improvements modal state ──
  const [impOpen,setImpOpen]=useState(false);
  const [impData,setImpData]=useState(null);       // { words:[{word,count}] }
  const [impLoading,setImpLoading]=useState(false);
  const [impTab,setImpTab]=useState("words");      // "words" | "story"
  const [impLang,setImpLang]=useState("all");      // "all" | "english" | "hindi"
  const [practWord,setPractWord]=useState(null);   // word being practiced
  const [practAttempts,setPractAttempts]=useState([]);  // [true/false]
  const [practListening,setPractListening]=useState(false);
  const [story,setStory]=useState(null);           // {story_text,material_id,wrong_words}
  const [storyLoading,setStoryLoading]=useState(false);
  const [storyLang,setStoryLang]=useState("english");
  const [impError,setImpError]=useState("");

  // Sidebar form state
  const [fTeacher,setFTeacher]=useState({name:"",email:"",password:"",subject:""});
  const [fStudent,setFStudent]=useState({name:"",class_name:"",roll_no:"",teacher_id:""});
  const [fMaterial,setFMaterial]=useState({title:"",language:"english",class_level:"",file:null});

  // Report state
  const [report,setReport]=useState("");
  const [reportLoading,setReportLoading]=useState(false);
  const [reportSessionIds,setReportSessionIds]=useState([]); // empty means all
  
  // Teacher Notes state
  const [noteEdit,setNoteEdit]=useState({}); // {session_id: "notes"}

  const wsRef=useRef(null); const closingRef=useRef(false); const streamRef=useRef(null);
  const actxRef=useRef(null); const workletRef=useRef(null); const sendTRef=useRef(null);
  const timerRef=useRef(null); const activeRef=useRef(false); const pcmRef=useRef([]);
  const passRef=useRef(null); const recRef=useRef(null); const expRef=useRef([]);
  const hwRef=useRef(0); const lockRef=useRef([]); const prevWordsRef=useRef([]);

  const student = useMemo(()=>students.find(s=>String(s.id)===String(selStudent)),[students,selStudent]);
  const material = useMemo(()=>materials.find(m=>String(m.id)===String(selMaterial)),[materials,selMaterial]);

  useEffect(()=>{activeRef.current=active;},[active]);

  const reload = useCallback(()=>{
    if (!token) return;
    authFetch(`${API}/students`).then(r=>r.json()).then(setStudents).catch(()=>{});
    authFetch(`${API}/materials`).then(r=>r.json()).then(setMaterials).catch(()=>{});
    authFetch(`${API}/teachers`).then(r=>r.json()).then(setTeachers).catch(()=>{});
  },[token]);
  useEffect(()=>{reload();},[reload]);

  useEffect(()=>{
    if(!selMaterial){setExpWords([]);setWStatus([]);setCurIdx(0);return;}
    authFetch(`${API}/materials/${selMaterial}/text`).then(r=>r.json()).then(p=>{
      const t=(p.text_content||"").replace(/\n/g," ").replace(/\s+/g," ").trim().split(" ").filter(Boolean);
      expRef.current=t; setExpWords(t); setWStatus(new Array(t.length).fill("unread"));
      lockRef.current=new Array(t.length).fill("unread"); setCurIdx(0); hwRef.current=0; prevWordsRef.current=[];
    }).catch(()=>setError("Failed to load passage."));
  },[selMaterial]);

  useEffect(()=>{
    if(!passRef.current) return;
    const el=passRef.current.querySelector(".word.current");
    if(el) el.scrollIntoView({behavior:"smooth",block:"nearest"});
  },[curIdx]);

  useEffect(()=>{
    if(!active){clearInterval(timerRef.current);timerRef.current=null;return;}
    const s=Date.now();
    timerRef.current=setInterval(()=>{const r=Math.max(0,180-Math.floor((Date.now()-s)/1000));setTimeLeft(r);if(r===0)stopReading(true);},1000);
    return()=>clearInterval(timerRef.current);
  },[active]);

  /* --- Speech Recognition --- */
  const srWatchRef=useRef(null);
  const rafRef=useRef(null); // for batching UI updates
  const pendingUpdate=useRef(null);
  const flushHighlight=()=>{ if(!pendingUpdate.current) return; const{mg,ei}=pendingUpdate.current; pendingUpdate.current=null; setWStatus(mg); setCurIdx(ei); };
  const scheduleHighlight=(mg,ei)=>{ pendingUpdate.current={mg,ei}; if(rafRef.current) cancelAnimationFrame(rafRef.current); rafRef.current=requestAnimationFrame(flushHighlight); };

  const startSR = useCallback((lang)=>{
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition; if(!SR) return;
    prevWordsRef.current=[];
    const r=new SR(); r.continuous=true; r.interimResults=true; r.lang=langCode(lang); r.maxAlternatives=3;
    recRef.current=r;
    r.onresult=(ev)=>{
      let finalWords=[]; let allWords=[];
      for(let i=0;i<ev.results.length;i++){
        // Try all alternatives and pick the best-matching transcript
        let bestTranscript=ev.results[i][0].transcript;
        if(ev.results[i].length>1){
          const exp=expRef.current;
          const ci=hwRef.current;
          if(ci<exp.length){
            let bestScore=-1;
            for(let a=0;a<ev.results[i].length;a++){
              const t=ev.results[i][a].transcript.trim().split(/\s+/).filter(Boolean);
              let score=0; for(const tw of t){if(fuzzy(exp[ci],tw)||fuzzy(exp[Math.min(ci+1,exp.length-1)],tw)) score++;}
              if(score>bestScore){bestScore=score;bestTranscript=ev.results[i][a].transcript;}
            }
          }
        }
        const w=bestTranscript.trim().split(/\s+/).filter(Boolean);
        allWords.push(...w);
        if(ev.results[i].isFinal) finalWords.push(...w);
      }
      const sp=[...prevWordsRef.current,...allWords];
      const exp=expRef.current; if(!exp.length) return;
      const{statuses,reachedIndex}=alignW(exp,sp);
      const ei=Math.max(reachedIndex,hwRef.current); hwRef.current=ei;
      const lk=lockRef.current; const mg=new Array(exp.length).fill("unread");
      for(let i=0;i<exp.length;i++){if(lk[i]!=="unread") mg[i]=lk[i]; else if(i<reachedIndex) mg[i]=statuses[i];}
      scheduleHighlight(mg,ei<exp.length?ei:exp.length-1);
      if(finalWords.length>0){
        const finSp=[...prevWordsRef.current,...finalWords];
        const{statuses:fs,reachedIndex:fi}=alignW(exp,finSp);
        const nl=[...lk];for(let i=0;i<fi;i++){if(nl[i]==="unread")nl[i]=fs[i];}lockRef.current=nl;
      }
    };
    r.onerror=()=>{};
    r.onend=()=>{
      if(activeRef.current&&recRef.current){
        const committed=lockRef.current.filter(s=>s!=="unread").length;
        prevWordsRef.current=expRef.current.slice(0,committed).map(w=>cleanW(w)).filter(Boolean);
        setTimeout(()=>{if(activeRef.current&&recRef.current){try{recRef.current.start();}catch{}}},30);
      }
    };
    r.start();
    // Watchdog: force-restart SR every 2.5s to prevent Chrome's long processing stalls
    if(srWatchRef.current) clearInterval(srWatchRef.current);
    srWatchRef.current=setInterval(()=>{
      if(!activeRef.current||!recRef.current) return;
      try{recRef.current.stop();}catch{}
    },3500);
  },[]);
  const stopSR=useCallback(()=>{
    if(srWatchRef.current){clearInterval(srWatchRef.current);srWatchRef.current=null;}
    if(recRef.current){recRef.current.onend=null;try{recRef.current.abort();}catch{}recRef.current=null;}
    prevWordsRef.current=[];
  },[]);

  /* --- Audio Stream --- */
  const startAudio=async()=>{
    const st=await navigator.mediaDevices.getUserMedia({audio:true}); streamRef.current=st;
    const ac=new AudioContext(); actxRef.current=ac;
    await ac.audioWorklet.addModule(new URL("./pcm-worklet.js",import.meta.url));
    const src=ac.createMediaStreamSource(st); const nd=new AudioWorkletNode(ac,"pcm-processor"); workletRef.current=nd;
    const g=ac.createGain(); g.gain.value=0;
    nd.port.onmessage=(e)=>{pcmRef.current.push(new Int16Array(e.data));};
    src.connect(nd); nd.connect(g); g.connect(ac.destination);
    sendTRef.current=setInterval(()=>{if(!pcmRef.current.length)return;const m=merge16(pcmRef.current);pcmRef.current=[];if(wsRef.current&&wsRef.current.readyState===WebSocket.OPEN)wsRef.current.send(JSON.stringify({type:"audio",data:b64(m)}));},80);
  };
  const stopAudio=()=>{
    if(sendTRef.current){clearInterval(sendTRef.current);sendTRef.current=null;}
    if(workletRef.current){workletRef.current.disconnect();workletRef.current=null;}
    if(actxRef.current){actxRef.current.close();actxRef.current=null;}
    if(streamRef.current){streamRef.current.getTracks().forEach(t=>t.stop());streamRef.current=null;}
    pcmRef.current=[];
  };

  /* --- Start / Stop --- */
  const startReading=async()=>{
    setError(""); if(!student||!material){setError("Select a student and material.");return;} if(activeRef.current) return;
    const n=expRef.current.length; setWStatus(new Array(n).fill("unread")); lockRef.current=new Array(n).fill("unread");
    setCurIdx(0); hwRef.current=0; setMetrics(null); setSessionId(null); setWsStatus("connecting"); setActive(true); setTimeLeft(180);
    closingRef.current=false;
    const ws=new WebSocket(WS_URL); wsRef.current=ws;
    ws.onopen=async()=>{
      const stype=material?.class_level==="practice"?"improvement":"normal";
      ws.send(JSON.stringify({type:"start",student_id:student.id,material_id:material.id,language:material.language,format:"pcm",sample_rate:16000,channels:1,sample_width:2,extension:".wav",session_type:stype}));
      setWsStatus("ready");
      try{await startAudio();startSR(material.language);}catch{setError("Microphone access failed.");stopReading(true);}
    };
    ws.onmessage=(ev)=>{
      const p=JSON.parse(ev.data);
      if(p.type==="ready") setWsStatus("streaming");
      if(p.type==="stopped"){setSessionId(p.session_id);setActive(false);setWsStatus("stopped");}
      if(p.type==="error"){setWsStatus("error");setError(p.message||"Error");setActive(false);}
    };
    ws.onerror=()=>{setWsStatus("error");setError("WebSocket error.");setActive(false);stopAudio();stopSR();};
    ws.onclose=()=>{if(closingRef.current){closingRef.current=false;return;}stopAudio();stopSR();if(activeRef.current){setActive(false);setWsStatus("closed");}};
  };

  const stopReading=(send)=>{
    stopSR(); setActive(false);
    if(wsRef.current&&wsRef.current.readyState===WebSocket.OPEN&&send) wsRef.current.send(JSON.stringify({type:"stop"}));
    else{ if(wsRef.current){closingRef.current=true;wsRef.current.close();wsRef.current=null;} stopAudio(); }
  };

  const resetSession=()=>{
    stopSR(); setActive(false); setMetrics(null); setSessionId(null); setEvaluating(false);
    if(wsRef.current){closingRef.current=true;try{wsRef.current.close();}catch{}wsRef.current=null;}
    stopAudio();
    const n=expRef.current.length; setWStatus(new Array(n).fill("unread")); lockRef.current=new Array(n).fill("unread");
    setCurIdx(0); hwRef.current=0; prevWordsRef.current=[]; setTimeLeft(180); setError(""); setWsStatus("idle");
  };

  /* --- Evaluate --- */
  const evaluate=async()=>{
    if(!sessionId) return; setEvaluating(true); setError("");
    try{
      const ctrl=new AbortController(); const tid=setTimeout(()=>ctrl.abort(),120000);
      const r=await authFetch(`${API}/reading/evaluate/${sessionId}`,{method:"POST",signal:ctrl.signal});
      clearTimeout(tid);
      if(!r.ok){ const err=await r.json().catch(()=>({})); throw new Error(err.detail||`Evaluation failed (${r.status})`); }
      const d=await r.json();
      setMetrics({accuracy:d.accuracy,fluency:d.fluency,completion:d.completion,pace_wpm:d.pace_wpm,pace_score:d.pace_score,pronunciation:d.pronunciation,final_score:d.final_score,grade:d.grade,transcript:d.transcript,ai_overview:d.ai_overview||""});
      if (d.statuses && d.statuses.length === expWords.length) {
        setWStatus(d.statuses);
      }
    }catch(e){
      if(e.name==="AbortError") setError("Evaluation timed out. The model may still be loading — please try again.");
      else setError(e.message||"Evaluation failed");
    }finally{setEvaluating(false);}
  };

  /* --- History --- */
  const fetchHistory=async(sid)=>{
    if(!sid){setHistory([]);return;}
    setHistLoading(true);
    try{const r=await authFetch(`${API}/reading/sessions/${sid}`);if(r.ok)setHistory(await r.json());else setHistory([]);}
    catch(e){setHistory([]);}
    finally{setHistLoading(false);}
  };
  useEffect(()=>{if(pageTab==="history"&&selStudent)fetchHistory(selStudent);},[pageTab,selStudent]);

  /* --- Improvements --- */
  const openImprovements=async()=>{
    if(!selStudent){setError("Select a student first.");return;}
    setImpOpen(true);setImpTab("words");setImpError("");setStory(null);setPractWord(null);
    setImpLoading(true);
    try{
      const r=await authFetch(`${API}/improvements/${selStudent}`);
      if(!r.ok) throw new Error("Failed to load improvements");
      setImpData(await r.json());
    }catch(e){setImpError(e.message);}
    finally{setImpLoading(false);}
  };

  const generateStory=async()=>{
    setStoryLoading(true);setImpError("");
    try{
      const r=await authFetch(`${API}/improvements/${selStudent}/story?language=${storyLang}`,{method:"POST"});
      if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail||"Story generation failed");}
      setStory(await r.json());
    }catch(e){setImpError(e.message);}
    finally{setStoryLoading(false);}
  };

  const saveNotes=async(sid)=>{
    const n = noteEdit[sid];
    try{
      const r=await authFetch(`${API}/reading/sessions/${sid}/notes`,{
        method:"PUT", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({notes:n||""})
      });
      if(r.ok) fetchHistory(selStudent);
    }catch(e){console.error(e);}
  };

  const generateReport=async()=>{
    if(!selStudent) return;
    setReportLoading(true); setReport("");
    try{
      const r=await authFetch(`${API}/improvements/${selStudent}/report`,{
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({session_ids: reportSessionIds})
      });
      if(!r.ok) throw new Error("Failed to generate report");
      const d = await r.json();
      setReport(d.report);
    }catch(e){console.error(e);}
    finally{setReportLoading(false);}
  };

  const speakWord=(word,lang)=>{
    const u=new SpeechSynthesisUtterance(word);
    u.lang=langCode(lang||material?.language||"english");
    u.rate=0.8;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  };

  const practiceSpeak=(word,lang)=>{
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){alert("Speech recognition not supported in this browser.");return;}
    setPractListening(true);
    const r=new SR();r.lang=langCode(lang||material?.language||"english");r.maxAlternatives=3;
    r.onresult=(ev)=>{
      let ok = false;
      for (let i = 0; i < ev.results[0].length; i++) {
        const heard = ev.results[0][i].transcript.trim();
        if (fuzzy(word, heard, 0.85)) { ok = true; break; }
      }
      setPractAttempts(prev=>[...prev,ok]);
      setPractListening(false);
    };
    r.onerror=()=>setPractListening(false);
    r.start();
  };

  const startPracticeStory=()=>{
    if(!story) return;
    setSelMaterial(String(story.material_id));
    setImpOpen(false);
    setTimeout(()=>setError(""),100);
  };

  /* --- Sidebar Submissions --- */
  const submitTeacher=async(e)=>{e.preventDefault();
    try{const r=await authFetch(`${API}/teachers`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(fTeacher)});if(!r.ok) throw new Error("Failed");setFTeacher({name:"",email:"",password:"",subject:""});reload();}catch(err){setError(err.message);}};
  const submitStudent=async(e)=>{e.preventDefault();
    const tid = user?.is_admin ? fStudent.teacher_id : user?.id;
    if(!tid){setError("Please select a teacher first.");return;}
    try{const r=await authFetch(`${API}/students`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...fStudent,teacher_id:parseInt(tid)})});if(!r.ok) throw new Error("Failed");setFStudent({name:"",class_name:"",roll_no:"",teacher_id:""});reload();}catch(err){setError(err.message);}};
  const submitMaterial=async(e)=>{e.preventDefault();
    const fd=new FormData(); fd.append("title",fMaterial.title); fd.append("language",fMaterial.language); fd.append("class_level",fMaterial.class_level); if(fMaterial.file) fd.append("file",fMaterial.file);
    try{const r=await authFetch(`${API}/materials/upload`,{method:"POST",body:fd});if(!r.ok) throw new Error("Failed");setFMaterial({title:"",language:"english",class_level:"",file:null});reload();}catch(err){setError(err.message);}};

  const deleteTeacher=async(id)=>{if(!confirm("Delete this teacher?"))return;try{await authFetch(`${API}/teachers/${id}`,{method:"DELETE"});reload();}catch{}}
  const deleteStudent=async(id)=>{if(!confirm("Delete this student?"))return;try{await authFetch(`${API}/students/${id}`,{method:"DELETE"});reload();}catch{}}
  const deleteMaterial=async(id)=>{if(!confirm("Delete this material?"))return;try{await authFetch(`${API}/materials/${id}`,{method:"DELETE"});reload();}catch{}}

  /* --- Derived --- */
  const dw=expWords.map((w,i)=>({word:w,status:i===curIdx&&wStatus[i]==="unread"?"current":wStatus[i]}));
  const prog=expWords.length>0?Math.round(curIdx/expWords.length*1000)/10:0;
  const sLabel=wsStatus==="streaming"?"● Listening":wsStatus==="connecting"?"◌ Connecting":wsStatus==="ready"?"◌ Ready":wsStatus==="stopped"?"■ Stopped":wsStatus==="error"?"✗ Error":"";

  const handleLogin = (data) => {
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem("vachanam_token", data.access_token);
    localStorage.setItem("vachanam_user", JSON.stringify(data.user));
    if (!data.user.requires_profile) reload();
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("vachanam_token");
    localStorage.removeItem("vachanam_user");
  };

  const submitProfile = async (e) => {
    e.preventDefault();
    setProfileLoading(true);
    try {
      const r = await authFetch(`${API}/auth/complete-profile`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: profileName, subject: profileSubject })
      });
      if (!r.ok) throw new Error("Failed to update profile");
      const updatedUser = await r.json();
      setUser(updatedUser);
      localStorage.setItem("vachanam_user", JSON.stringify(updatedUser));
      reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setProfileLoading(false);
    }
  };

  if (!token) return <Login onLogin={handleLogin} />;

  if (user && user.requires_profile) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
        <div style={{ background: 'var(--surface)', padding: '40px', borderRadius: '24px', boxShadow: 'var(--shadow)', width: '100%', maxWidth: '400px' }}>
          <h2 style={{ textAlign: 'center', margin: '0 0 24px', color: 'var(--ink)' }}>Complete Your Profile</h2>
          <form onSubmit={submitProfile} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <input placeholder="Your Full Name" required value={profileName} onChange={e => setProfileName(e.target.value)} style={{ padding: '12px', borderRadius: '12px', border: '1px solid var(--ink4)', fontSize: '16px' }} />
            <input placeholder="Subject you teach (e.g. English, Hindi)" required value={profileSubject} onChange={e => setProfileSubject(e.target.value)} style={{ padding: '12px', borderRadius: '12px', border: '1px solid var(--ink4)', fontSize: '16px' }} />
            <button type="submit" disabled={profileLoading} style={{ padding: '14px', borderRadius: '12px', background: 'var(--primary)', color: 'white', border: 'none', fontSize: '16px', fontWeight: '600', cursor: 'pointer' }}>
              {profileLoading ? "Saving..." : "Continue to Dashboard"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {/* 100% width header */}
      <header className="header-container">
        <div className="header-content">
          <div className="title-area">
            <h1 className="title"><img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Books/3D/books_3d.png" alt="Books" className="icon-3d large" style={{width:42, height:42}} /> Vāchanam</h1>
            <p className="subtitle">Learning Made Fun</p>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '16px'}}>
            {sLabel&&<div className={`status-pill ${wsStatus==="streaming"?"live":""}`}>{sLabel}</div>}
            <div style={{display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--ink2)', fontWeight: '500'}}>
              <span style={{background: 'var(--ink5)', padding: '6px 12px', borderRadius: '20px', fontSize: '14px'}}>{user?.name} {user?.is_admin ? '(Admin)' : ''}</span>
              <button onClick={handleLogout} style={{background: 'transparent', border: 'none', color: 'var(--ink2)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '6px'}} title="Logout">
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="main-content">
        {/* Page-level tabs */}
        <div className="page-tabs">
          <button className={`page-tab ${pageTab==="reading"?"active":""}`} onClick={()=>setPageTab("reading")}><BookOpen className="icon-3d tab" /> Reading</button>
          <button className={`page-tab ${pageTab==="history"?"active":""}`} onClick={()=>setPageTab("history")}><Activity className="icon-3d tab" /> Progress</button>
          <button className={`page-tab ${pageTab==="reports"?"active":""}`} onClick={()=>setPageTab("reports")}><FileText className="icon-3d tab" /> Reports</button>
          <button className={`page-tab ${pageTab==="management"?"active":""}`} onClick={()=>setPageTab("management")}><PlusCircle className="icon-3d tab" /> Add Activity</button>
        </div>

        {/* ── READING TAB ── */}
        {pageTab==="reading"&&(
        <main className="layout">
          <section className="controls-bar">
            {user?.is_admin && (
              <div className="field-inline">
                <label><Users className="icon-3d btn" style={{width:14,height:14}} /> TEACHER</label>
                <select value={selTeacher} onChange={e=>{setSelTeacher(e.target.value);setSelStudent("");}} disabled={active}>
                  <option value="">All Teachers</option>
                  {teachers.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            )}
            <div className="field-inline">
              <label><GraduationCap className="icon-3d btn" style={{width:14,height:14}} /> STUDENT</label>
              <select value={selStudent} onChange={e=>setSelStudent(e.target.value)} disabled={active}>
                <option value="">Select Student</option>
                {students.filter(s=>!selTeacher||String(s.teacher_id)===String(selTeacher)).map(s=><option key={s.id} value={s.id}>{s.name} (Class {s.class_name})</option>)}
              </select>
            </div>
            <div className="field-inline">
              <label><BookText className="icon-3d btn" style={{width:14,height:14}} /> MATERIAL</label>
              <select value={selMaterial} onChange={e=>setSelMaterial(e.target.value)} disabled={active}>
                <option value="">Select Material</option>
                {materials.map(m=><option key={m.id} value={m.id}>{m.title} ({m.language})</option>)}
              </select>
            </div>
            <div className="btn-row">
              <button className="start-btn" onClick={startReading} disabled={active}>{active? <><Activity className="icon-3d btn" /> Reading…</> : <><Play className="icon-3d btn" /> Start</>}</button>
              <button className="secondary stop-btn" onClick={()=>stopReading(true)} disabled={!active}><Square className="icon-3d btn" /> Stop</button>
              <button className="secondary reset-btn" onClick={resetSession} disabled={active}><RotateCcw className="icon-3d btn" /> Reset</button>
              {selStudent&&<button className="imp-btn" onClick={openImprovements} disabled={active}><TrendingUp className="icon-3d btn" /> Improvements</button>}
            </div>
          </section>

          {active&&(
            <div className="timer-bar">
              <span className="timer-label"><Activity className="icon-3d btn" /> Time Remaining</span>
              <span className={`timer-value ${timeLeft<=30?"urgent":""}`}>{fmt(timeLeft)}</span>
            </div>
          )}

          <section className="panel passage-panel">
            <div className="panel-header">
              <span><img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Open%20book/3D/open_book_3d.png" alt="Open Book" className="icon-3d panel-icon" style={{width:24, height:24, filter:'drop-shadow(0px 2px 4px rgba(0,0,0,0.15))'}} /> Reading Passage</span>
              <span className="word-count">{expWords.length>0&&`${curIdx} / ${expWords.length}`}</span>
            </div>
            
            {dw.length===0 ? (
              <div className="empty-state">
                <div className="empty-icon-wrapper">
                  <div className="empty-icon"><img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Closed%20book/3D/closed_book_3d.png" alt="Closed Book" style={{width:72, height:72, filter: "drop-shadow(0px 8px 12px rgba(0,0,0,0.15))", transform: "perspective(200px) translateZ(10px)"}} /></div>
                </div>
                <div className="empty-title">Select a material to load the passage.</div>
                <div className="empty-subtitle">Choose from our collection of engaging stories<br/>and learning materials!</div>
              </div>
            ) : (
              <>
                <div className="passage" ref={passRef}>
                  {dw.map((item,i)=><span key={`w-${i}`} className={`word ${item.status}`}>{item.word} </span>)}
                </div>
                <div className="progress"><div className="bar" style={{width:`${prog}%`}}/></div>
              </>
            )}
          </section>

          {sessionId&&!metrics&&(
            <div className="evaluate-row">
              <button className="evaluate-btn" onClick={evaluate} disabled={evaluating}>
                {evaluating? <><Activity className="icon-3d btn" /> Evaluating…</> : <><BarChart3 className="icon-3d btn" /> Evaluate Reading</>}
              </button>
            </div>
          )}

          {metrics&&(
            <section className="panel metrics-panel">
              <div className="panel-header">Evaluation Results</div>
              <div className="metrics-grid">
                <div className="metric-card accent"><div className="metric-label">Final Score</div><div className="metric-value">{metrics.final_score}</div></div>
                <div className="metric-card gold"><div className="metric-label">Grade</div><div className="metric-value grade">{metrics.grade}</div></div>
                <div className="metric-card"><div className="metric-label">Accuracy</div><div className="metric-value">{metrics.accuracy}%</div></div>
                <div className="metric-card"><div className="metric-label">Fluency</div><div className="metric-value">{metrics.fluency}%</div></div>
                <div className="metric-card"><div className="metric-label">Completion</div><div className="metric-value">{metrics.completion}%</div></div>
                <div className="metric-card"><div className="metric-label">Pronunciation</div><div className="metric-value">{metrics.pronunciation}%</div></div>
                <div className="metric-card"><div className="metric-label">Pace</div><div className="metric-value">{metrics.pace_wpm} wpm</div></div>
                <div className="metric-card"><div className="metric-label">Pace Score</div><div className="metric-value">{metrics.pace_score}%</div></div>
              </div>
              {metrics.ai_overview&&(
                <div className="ai-overview-box">
                  <span className="ai-overview-icon"><Bot className="icon-3d large" style={{margin:0, width:26, height:26}} /></span>
                  <div>
                    <div className="ai-overview-title">AI Feedback</div>
                    <p className="ai-overview-text">{metrics.ai_overview}</p>
                  </div>
                </div>
              )}
              {metrics.transcript&&(
                <div className="transcript-section">
                  <h4 className="transcript-title"><FileText className="icon-3d panel-icon" /> Transcription</h4>
                  <p className="transcript-text">{metrics.transcript}</p>
                </div>
              )}
            </section>
          )}

          {error&&<div className="error">{error}</div>}
        </main>
        )}

        {/* ── HISTORY TAB ── */}
        {pageTab==="history"&&(
        <main className="layout">
          <section className="controls-bar">
            {user?.is_admin && (
              <div className="field-inline">
                <label>Teacher</label>
                <select value={selTeacher} onChange={e=>{setSelTeacher(e.target.value);setSelStudent("");}}>
                  <option value="">All teachers</option>
                  {teachers.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            )}
            <div className="field-inline">
              <label>Student</label>
              <select value={selStudent} onChange={e=>setSelStudent(e.target.value)}>
                <option value="">Select student</option>
                {students.filter(s=>!selTeacher||String(s.teacher_id)===String(selTeacher)).map(s=><option key={s.id} value={s.id}>{s.name} (Class {s.class_name})</option>)}
              </select>
            </div>
            <div className="btn-row">
              {selStudent&&<button className="imp-btn" onClick={openImprovements}><TrendingUp className="icon-3d btn" /> Improvements</button>}
            </div>
          </section>

          {!selStudent&&<div className="history-empty"><AlertCircle className="icon-3d btn" style={{color:"var(--ink3)"}}/> Select a student to view their reading history.</div>}
          {selStudent&&histLoading&&<div className="history-empty">Loading history…</div>}
          {selStudent&&!histLoading&&history.length===0&&<div className="history-empty">No evaluated sessions yet for this student.</div>}
          {selStudent&&!histLoading&&history.length>0&&(
            <>
              {/* Performance Charts */}
              <div className="panel" style={{marginBottom: 20}}>
                <div className="panel-header">Performance Over Time</div>
                <div style={{height: 250, width: '100%'}}>
                  <ResponsiveContainer>
                    <LineChart data={[...history].reverse()} margin={{top:10, right:30, left:0, bottom:0}}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e0e4f0"/>
                      <XAxis dataKey="created_at" tickFormatter={(t)=>new Date(t).toLocaleDateString('en-IN',{month:'short',day:'numeric'})} stroke="#9498b8" fontSize={12}/>
                      <YAxis stroke="#9498b8" fontSize={12} domain={[0, 100]} />
                      <Tooltip contentStyle={{borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)'}} />
                      <Legend />
                      <Line type="monotone" dataKey="final_score" name="Overall Score" stroke="#6c5ce7" strokeWidth={3} activeDot={{r: 8}} />
                      <Line type="monotone" dataKey="accuracy" name="Accuracy" stroke="#00b894" strokeWidth={2} />
                      <Line type="monotone" dataKey="fluency" name="Fluency" stroke="#ff9f43" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="history-list">
                {history.map(h=>{
                const wrongArr=JSON.parse(h.wrong_words||"[]");
                const isExpanded=expandedSession===h.id;
                return(
                <div key={h.id} className="history-card">
                  <div className="history-card-top">
                    <div style={{display:"flex",alignItems:"center",gap:10}}>
                      <span className="history-card-title">{h.material_title}</span>
                      <span className="history-card-lang">{h.material_language}</span>
                      <span className={`history-card-grade ${h.grade}`}>{h.grade}</span>
                    </div>
                    <span className="history-card-date">{new Date(h.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})} · {new Date(h.created_at).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}</span>
                  </div>
                  <div className="history-metrics-row">
                    <div className="history-metric"><span className="history-metric-label">Score</span><span className="history-metric-value">{h.final_score}</span></div>
                    <div className="history-metric"><span className="history-metric-label">Accuracy</span><span className="history-metric-value">{h.accuracy}%</span></div>
                    <div className="history-metric"><span className="history-metric-label">Fluency</span><span className="history-metric-value">{h.fluency}%</span></div>
                    <div className="history-metric"><span className="history-metric-label">Completion</span><span className="history-metric-value">{h.completion}%</span></div>
                    <div className="history-metric"><span className="history-metric-label">Pace</span><span className="history-metric-value">{h.pace_wpm} wpm</span></div>
                    <div className="history-metric"><span className="history-metric-label">Pronunciation</span><span className="history-metric-value">{h.pronunciation}%</span></div>
                  </div>
                  {wrongArr.length>0&&(
                    <div className="history-wrong">
                      <span className="history-wrong-label">Wrong words:</span>
                      {wrongArr.slice(0,8).map((w,i)=><span key={i} className="history-wrong-tag">{w}</span>)}
                      {wrongArr.length>8&&<span className="history-wrong-tag">+{wrongArr.length-8}</span>}
                    </div>
                  )}
                  <div className="history-expand">
                    <button className="history-expand-btn" onClick={()=>setExpandedSession(isExpanded?null:h.id)}>
                      {isExpanded?"▲ Hide details":"▼ Show details"}
                    </button>
                  </div>
                  {isExpanded&&(
                    <div style={{marginTop:12}}>
                      {h.ai_overview&&(
                        <div className="ai-overview-box" style={{margin:"0 0 12px"}}>
                          <span className="ai-overview-icon"><Bot className="icon-3d large" style={{margin:0, width:26, height:26}} /></span>
                          <div><div className="ai-overview-title">AI Feedback</div><p className="ai-overview-text">{h.ai_overview}</p></div>
                        </div>
                      )}
                      {h.transcript&&(
                        <div><h4 className="transcript-title"><FileText className="icon-3d panel-icon" /> Transcription</h4><p className="transcript-text">{h.transcript}</p></div>
                      )}
                      {wrongArr.length>8&&(
                        <div className="history-wrong" style={{marginTop:10}}>
                          <span className="history-wrong-label">All wrong words:</span>
                          {wrongArr.map((w,i)=><span key={i} className="history-wrong-tag">{w}</span>)}
                        </div>
                      )}
                      
                      {/* Teacher Notes Area */}
                      <div className="teacher-notes-section" style={{marginTop:16}}>
                        <h4 className="transcript-title"><FileText className="icon-3d panel-icon" /> Teacher Notes</h4>
                        <textarea 
                          className="notes-textarea" 
                          placeholder="Add your notes about this session..."
                          value={noteEdit[h.id]!==undefined?noteEdit[h.id]:(h.teacher_notes||"")}
                          onChange={e=>setNoteEdit({...noteEdit,[h.id]:e.target.value})}
                        />
                        <button className="wc-btn speak" style={{marginTop:8, width:"auto"}} onClick={()=>saveNotes(h.id)}>
                          💾 Save Notes
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );})}
              </div>
            </>
          )}
        </main>
        )}

        {/* ── MANAGEMENT TAB ── */}
        {pageTab==="management"&&(
        <main className="layout">
          <div className="management-grid">
            {user?.is_admin && (
              <div className="manage-card">
                <h3><Users className="icon-3d manage" /> Add Teacher</h3>
                <form className="manage-form" onSubmit={submitTeacher}>
                  <input placeholder="Name" required value={fTeacher.name} onChange={e=>setFTeacher({...fTeacher,name:e.target.value})}/>
                  <input type="email" placeholder="Email" required value={fTeacher.email} onChange={e=>setFTeacher({...fTeacher,email:e.target.value})}/>
                  <input type="password" placeholder="Temporary Password" required value={fTeacher.password} onChange={e=>setFTeacher({...fTeacher,password:e.target.value})}/>
                  <input placeholder="Subject" required value={fTeacher.subject} onChange={e=>setFTeacher({...fTeacher,subject:e.target.value})}/>
                  <button type="submit">Add Teacher</button>
                </form>
                {teachers.length>0&&(
                  <div className="manage-list">
                    {teachers.map(t=>(
                      <div key={t.id} className="manage-list-item" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                        <span>{t.name} — {t.subject}</span>
                        <button className="del-btn" onClick={()=>deleteTeacher(t.id)}><Trash2 className="icon-3d btn" style={{margin:0, width:14,height:14}}/></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="manage-card">
              <h3><GraduationCap className="icon-3d manage" /> Add Student</h3>
              <form className="manage-form" onSubmit={submitStudent}>
                {user?.is_admin && (
                  <>
                    <select required value={fStudent.teacher_id} onChange={e=>setFStudent({...fStudent,teacher_id:e.target.value})}>
                      <option value="">Select Teacher *</option>
                      {teachers.map(t=><option key={t.id} value={t.id}>{t.name} ({t.subject})</option>)}
                    </select>
                    {teachers.length===0&&<div className="sidebar-hint" style={{marginBottom:10}}>⚠ Add a teacher first</div>}
                  </>
                )}
                <input placeholder="Name" required value={fStudent.name} onChange={e=>setFStudent({...fStudent,name:e.target.value})}/>
                <input placeholder="Class" required value={fStudent.class_name} onChange={e=>setFStudent({...fStudent,class_name:e.target.value})}/>
                <input placeholder="Roll No" required value={fStudent.roll_no} onChange={e=>setFStudent({...fStudent,roll_no:e.target.value})}/>
                <button type="submit" disabled={user?.is_admin && teachers.length===0}>Add Student</button>
              </form>
              {students.length>0&&(
                <div className="manage-list">
                  {students.map(s=>(
                    <div key={s.id} className="manage-list-item" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                      <span>{s.name} ({s.class_name})</span>
                      <button className="del-btn" onClick={()=>deleteStudent(s.id)}><Trash2 className="icon-3d btn" style={{margin:0, width:14,height:14}}/></button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="manage-card">
              <h3><FilePlus className="icon-3d manage" /> Add Material</h3>
              <form className="manage-form" onSubmit={submitMaterial}>
                <input placeholder="Title" required value={fMaterial.title} onChange={e=>setFMaterial({...fMaterial,title:e.target.value})}/>
                <select value={fMaterial.language} onChange={e=>setFMaterial({...fMaterial,language:e.target.value})}>
                  <option value="english">English</option><option value="hindi">Hindi</option>
                </select>
                <input placeholder="Class Level" required value={fMaterial.class_level} onChange={e=>setFMaterial({...fMaterial,class_level:e.target.value})}/>
                <input type="file" accept=".pdf" onChange={e=>setFMaterial({...fMaterial,file:e.target.files[0]})}/>
                <button type="submit">Upload Material</button>
              </form>
              {materials.length>0&&(
                <div className="manage-list">
                  {materials.map(m=>(
                    <div key={m.id} className="manage-list-item" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                      <span>{m.title} ({m.language})</span>
                      <button className="del-btn" onClick={()=>deleteMaterial(m.id)}><Trash2 className="icon-3d btn" style={{margin:0, width:14,height:14}}/></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
        )}

        {/* ── REPORTS TAB ── */}
        {pageTab==="reports"&&(
        <main className="layout">
          <section className="controls-bar">
            {user?.is_admin && (
              <div className="field-inline">
                <label>Teacher</label>
                <select value={selTeacher} onChange={e=>{setSelTeacher(e.target.value);setSelStudent("");}}>
                  <option value="">All teachers</option>
                  {teachers.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            )}
            <div className="field-inline">
              <label>Student</label>
              <select value={selStudent} onChange={e=>setSelStudent(e.target.value)}>
                <option value="">Select student</option>
                {students.filter(s=>!selTeacher||String(s.teacher_id)===String(selTeacher)).map(s=><option key={s.id} value={s.id}>{s.name} (Class {s.class_name})</option>)}
              </select>
            </div>
            <div className="field-inline">
              <label>Sessions</label>
              <select value={reportSessionIds.length>0?"selected":"all"} onChange={e=>setReportSessionIds(e.target.value==="all"?[]:[...history.slice(0,3).map(h=>h.id)])}>
                <option value="all">All History</option>
                <option value="selected">Recent 3 Sessions</option>
              </select>
            </div>
            <div className="btn-row">
              <button className="evaluate-btn" style={{padding:"12px 24px", fontSize:"14px", borderRadius:"10px"}} onClick={generateReport} disabled={!selStudent||reportLoading}>
                {reportLoading? <><Activity className="icon-3d btn" /> Generating…</> : <><FileText className="icon-3d btn" /> Generate AI Report</>}
              </button>
            </div>
          </section>

          {!selStudent&&<div className="history-empty"><AlertCircle className="icon-3d btn" style={{color:"var(--ink3)"}}/> Select a student to generate a report.</div>}
          
          {report&&(
            <div className="panel report-panel">
              <div className="panel-header"><TrendingUp className="icon-3d panel-icon" /> Student Progress Report</div>
              <div className="report-content markdown-body" style={{lineHeight: 1.8, fontSize: 15}}>
                <ReactMarkdown>{report}</ReactMarkdown>
              </div>
            </div>
          )}
        </main>
        )}
      </div>

      {/* ── Improvements Modal ── */}
      {impOpen&&(
        <div className="imp-overlay" onClick={e=>{if(e.target.classList.contains('imp-overlay'))setImpOpen(false);}}>
          <div className="imp-modal">
            <div className="imp-modal-header">
              <h2><TrendingUp className="icon-3d large" style={{width: 30, height: 30}} /> Improvements — {student?.name}</h2>
              <button className="imp-close" onClick={()=>setImpOpen(false)}>✕</button>
            </div>
            <div className="imp-tabs">
              <button className={`imp-tab ${impTab==="words"?"active":""}`} onClick={()=>setImpTab("words")}><Edit3 className="icon-3d tab" /> Wrong Words</button>
              <button className={`imp-tab ${impTab==="story"?"active":""}`} onClick={()=>setImpTab("story")}><BookOpen className="icon-3d tab" /> Practice Story</button>
              {impTab==="words"&&(
                <select
                  value={impLang}
                  onChange={e=>setImpLang(e.target.value)}
                  className="imp-lang-select"
                >
                  <option value="all">✦ All</option>
                  <option value="hindi">🇮🇳 Hindi</option>
                  <option value="english">🇬🇧 English</option>
                </select>
              )}
            </div>

            {impError&&<div className="error" style={{margin:"0 0 12px"}}>{impError}</div>}

            {impTab==="words"&&(
              <div>
                {impLoading&&<p className="notice">Loading wrong words…</p>}
                {!impLoading&&impData&&(
                  <>
                    <p className="imp-subtitle" style={{marginBottom:14}}>Words this student has struggled with across all sessions</p>
                    {(()=>{
                      const langNorm = w => {
                        const v = (w||"english").trim().toLowerCase();
                        return v==="en"?"english":v==="hi"?"hindi":v;
                      };
                      const filtered = impData.words.filter(({lang})=>{
                        if(impLang==="all") return true;
                        return langNorm(lang)===impLang.toLowerCase();
                      });
                      if(filtered.length===0) return <p className="notice">No wrong words for this language yet — complete a reading session first.</p>;
                      return (
                        <div className="word-card-grid">
                          {filtered.map(({word,count,lang})=>{
                            const l=langNorm(lang);
                            const countClass=count>5?"count-red":count<3?"count-green":"count-orange";
                            const countIcon=count>5?"⚠":count<3?"✓":"🕒";
                            return(
                            <div key={word} className={`word-card ${practWord===word?"active":""}`}>
                              <span className={`word-card-lang ${l}`}>
                                📖 {l.charAt(0).toUpperCase()+l.slice(1)}
                              </span>
                              <div className={`word-card-word ww-${l}`}>{word}</div>
                              <div className={`word-card-count ${countClass}`}>
                                {countIcon} {count}× wrong
                              </div>
                              <div className="word-card-actions">
                                <button className="wc-btn" onClick={()=>speakWord(word,lang)}><Headphones className="icon-3d btn" /> Hear</button>
                                <button className="wc-btn practice" onClick={()=>{setPractWord(word);setPractAttempts([]);}}>
                                  ✏ Practice
                                </button>
                              </div>
                              {practWord===word&&(
                                <div className="pract-widget">
                                  <div className="pract-target">Say: <strong>{word}</strong></div>
                                  <div className="pract-attempts">
                                    {practAttempts.map((ok,i)=><span key={i} className={ok?"pract-ok":"pract-fail"}>{ok?"✓":"✗"}</span>)}
                                    {practAttempts.length<3&&<span className="pract-pending">{3-practAttempts.length} left</span>}
                                  </div>
                                  {practAttempts.length>=3&&practAttempts.filter(Boolean).length>=3
                                    ?<div className="pract-mastered">🎉 Mastered! Well done!</div>
                                    :practAttempts.length>=3
                                      ?<><div className="pract-retry">Keep trying!</div><button className="wc-btn" onClick={()=>setPractAttempts([])}>↺ Retry</button></>
                                      :<button className="wc-btn speak" onClick={()=>practiceSpeak(word,lang)} disabled={practListening}>
                                        {practListening?"🎙 Listening…":"🎤 Speak Now"}
                                      </button>
                                  }
                                </div>
                              )}
                            </div>
                          );})}
                        </div>
                      );
                    })()}
                  </>
                )}
              </div>
            )}

            {impTab==="story"&&(
              <div>
                {!story&&(
                  <div className="story-generate-area">
                    <p className="imp-subtitle">Choose a language and generate a personalised practice story from the words your student finds hardest.</p>
                    <div className="lang-selector">
                      <button className={`lang-btn ${storyLang==="english"?"active":""}`} onClick={()=>setStoryLang("english")}>🇬🇧 English</button>
                      <button className={`lang-btn ${storyLang==="hindi"?"active":""}`} onClick={()=>setStoryLang("hindi")}>🇮🇳 Hindi</button>
                    </div>
                    <button className="evaluate-btn" onClick={generateStory} disabled={storyLoading}>
                      {storyLoading?"✨ Generating…":"✨ Generate Practice Story"}
                    </button>
                  </div>
                )}
                {story&&(
                  <div className="story-area">
                    <div className="story-passage">
                      <h4 className="story-title"><BookOpen className="icon-3d tab" /> Practice Story</h4>
                      <p className="story-text">{story.story_text}</p>
                      <div className="story-words">
                        <span className="story-words-label">Focus words: </span>
                        {story.wrong_words.slice(0,10).map(w=><span key={w} className="story-word-tag">{w}</span>)}
                      </div>
                    </div>
                    <div className="story-actions">
                      <button className="wc-btn" onClick={()=>setStory(null)}>↺ Regenerate</button>
                      <button className="evaluate-btn" onClick={startPracticeStory}>▶ Start Reading Practice</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
