# # pytubefix_functions_single.py
# # version: 2025-10-15
# from pytubefix import YouTube
# from pytubefix import exceptions as ptfx_exc
# from pathlib import Path
# from datetime import datetime
# from urllib.parse import urlparse, parse_qs, unquote
# import dateparser, json, jsonlines, re, os, time

# class Pytubefix_Single:
#     @staticmethod
#     def parse_partial_date(date_str):
#         parsed=dateparser.parse(date_str,settings={'PREFER_DAY_OF_MONTH':'first','PREFER_DATES_FROM':'past'})
#         if not parsed: raise ValueError(f"Invalid date input: '{date_str}'")
#         return parsed.date()
#     @staticmethod
#     def extract_source(url):
#         m=re.search(r'@([^/]+)',url)
#         return m.group(1) if m else 'Unknown'
#     @staticmethod
#     def generate_output_path(file,nesting_level=4):
#         script_path=Path(file).resolve()
#         country=script_path.parents[nesting_level-3].name
#         script_name=script_path.stem
#         output_path=script_path.parents[nesting_level]/'data'/country/script_name
#         print(f'This is the generated output path: {output_path}')
#         return output_path
#     @staticmethod
#     def _normalize_yt_url(url:str)->str:
#         u=unquote(url.strip()); p=urlparse(u); host=(p.netloc or "").lower(); path=p.path or ""; q=parse_qs(p.query); vid=(q.get("v") or [""])[0]
#         if "watch" in path and vid: return f"https://www.youtube.com/watch?v={vid}"
#         if "youtu.be" in host:
#             vid=path.lstrip("/").split("/")[0]
#             if vid: return f"https://www.youtube.com/watch?v={vid}"
#         if "/embed/" in path:
#             vid=path.split("/embed/")[-1].split("/")[0].split("?")[0].split("&")[0]
#             if vid: return f"https://www.youtube.com/watch?v={vid}"
#         if vid: return f"https://www.youtube.com/watch?v={vid}"
#         return u
#     @staticmethod
#     def _extract_video_id(url:str)->str:
#         try:
#             p=urlparse(url); q=parse_qs(p.query); vid=(q.get("v") or [""])[0]
#             if vid: return vid
#             if "youtu.be" in (p.netloc or "").lower(): return (p.path or "").lstrip("/").split("/")[0]
#             if "/embed/" in (p.path or ""): return p.path.split("/embed/")[-1].split("/")[0].split("?")[0].split("&")[0]
#         except Exception: pass
#         return ""
#     @staticmethod
#     def _append_failure(failed_path:Path,title:str,video_id:str,err:str,url_for_log:str):
#         try:
#             seen=set()
#             if failed_path.exists():
#                 with jsonlines.open(failed_path,mode='r') as r:
#                     for item in r:
#                         try:
#                             _,v,_=item.get("error",["","",""]); u=item.get("url","")
#                             if v: seen.add(f"VID::{v}")
#                             if u: seen.add(f"URL::{u}")
#                         except Exception: pass
#             key=f"VID::{video_id}" if video_id else f"URL::{url_for_log}"
#             if key not in seen:
#                 with jsonlines.open(failed_path,mode='a') as w:
#                     w.write({"error":[title,video_id,str(err)],"url":url_for_log,"retries":0})
#         except Exception as e: print(f"Failed to log failure for {url_for_log}: {e}")
#     @staticmethod
#     def from_video_jsonlines(url:str,output_path:Path,source:str='',from_date=None,to_date=None):
#         url=Pytubefix_Single._normalize_yt_url(url)
#         output_path=Path(output_path); output_path.mkdir(parents=True,exist_ok=True)
#         jsonlines_path=output_path/'videos.jl'; failed_path=output_path/'not_downloaded.jl'
#         if not source: source=Pytubefix_Single.extract_source(url)
#         timestamp=datetime.now().strftime('%Y-%m-%d')
#         existing=set()
#         if jsonlines_path.exists():
#             with jsonlines_path.open('r',encoding='utf-8') as f:
#                 for line in f:
#                     try: existing.add(json.loads(line)['video_link'])
#                     except Exception: pass
#         try:
#             yt=YouTube(url,use_oauth=True,allow_oauth_cache=True)
#         except Exception as e_ctor:
#             print(f"Skipping (cannot construct YouTube): {url} — {e_ctor}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",Pytubefix_Single._extract_video_id(url),f"CTOR:{e_ctor}",url); return
#         if getattr(yt,"watch_url",url) in existing:
#             print(f"Already in videos.jl, skipping metadata: {getattr(yt,'watch_url',url)}"); return
#         try:
#             yt.check_availability()
#         except (ptfx_exc.VideoPrivate,ptfx_exc.VideoUnavailable,ptfx_exc.AgeRestrictedError) as e_av:
#             print(f"Skipping (unavailable/private): {url} — {e_av}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or Pytubefix_Single._extract_video_id(url),f"AVAIL:{e_av}",url); return
#         except Exception as e_avx:
#             print(f"Skipping (unexpected availability): {url} — {type(e_avx).__name__}: {e_avx}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or Pytubefix_Single._extract_video_id(url),f"AVAIL_UNK:{e_avx}",url); return
#         try:
#             pub_date_write=""
#             if getattr(yt,"publish_date",None):
#                 pdate=yt.publish_date.date()
#                 if from_date and pdate<from_date: print("Older than from_date — skipping metadata."); return
#                 if to_date and pdate>to_date: print("Newer than to_date — skipping metadata."); return
#                 pub_date_write=yt.publish_date.isoformat()
#             try: title=yt.title
#             except Exception: title="(unknown title)"
#             data={'scrape_date':timestamp,'video_title':title,'source':source,'publication_date':pub_date_write,'video_link':yt.watch_url,'video_id':yt.video_id}
#             with jsonlines.open(jsonlines_path,mode='a') as w: w.write_all([data])
#             print(f"💾 Wrote metadata: {title}")
#         except Exception as e_meta:
#             print(f"Failed metadata for {url}: {e_meta}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or Pytubefix_Single._extract_video_id(url),f"META:{e_meta}",url)
#     @staticmethod
#     def from_video_audio(url:str,output_path:Path,from_date=None,to_date=None,check_for_downloaded=False):
#         url=Pytubefix_Single._normalize_yt_url(url)
#         output_path=Path(output_path); output_path.mkdir(parents=True,exist_ok=True)
#         m4a_folder=output_path/'m4a_files'; m4a_folder.mkdir(parents=True,exist_ok=True)
#         failed_path=output_path/'not_downloaded.jl'
#         try:
#             yt=YouTube(url,use_oauth=True,allow_oauth_cache=True)
#         except Exception as e_ctor:
#             print(f"Skipping (cannot construct YouTube): {url} — {e_ctor}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",Pytubefix_Single._extract_video_id(url),f"CTOR:{e_ctor}",url); return
#         try:
#             yt.check_availability()
#         except (ptfx_exc.VideoPrivate,ptfx_exc.VideoUnavailable,ptfx_exc.AgeRestrictedError) as e_av:
#             print(f"Skipping (unavailable/private): {url} — {e_av}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or Pytubefix_Single._extract_video_id(url),f"AVAIL:{e_av}",url); return
#         except Exception as e_avx:
#             print(f"Skipping (unexpected availability): {url} — {type(e_avx).__name__}: {e_avx}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or Pytubefix_Single._extract_video_id(url),f"AVAIL_UNK:{e_avx}",url); return
#         if getattr(yt,"publish_date",None):
#             pdate=yt.publish_date.date()
#             if from_date and pdate<from_date: print("Older than from_date — skipping audio."); return
#             if to_date and pdate>to_date: print("Newer than to_date — skipping audio."); return
#         try: vid=yt.video_id
#         except Exception: vid=Pytubefix_Single._extract_video_id(url)
#         fname=f"{vid}.m4a"; fpath=m4a_folder/fname
#         if fpath.exists() and check_for_downloaded:
#             print(f"Already downloaded, skipping audio: {fname}"); return
#         try:
#             stream=yt.streams.filter(only_audio=True).first()
#             if stream is None: raise ValueError("No audio stream available.")
#             stream.download(output_path=m4a_folder,filename=fname)
#             try: title=yt.title
#             except Exception: title="(unknown title)"
#             print(f"✅ Downloaded audio: {title}")
#         except Exception as e_dl:
#             print(f"Failed audio for {url}: {e_dl}")
#             Pytubefix_Single._append_failure(failed_path,"(unknown title)",vid or "",f"DOWNLOAD:{e_dl}",url)
#     @staticmethod
#     def pytubefix_from_video(url:str,file,nesting_level=4,source:str='',output_path=None,from_date=None,to_date=None,check_for_downloaded=False):
#         generated_output=Path(output_path) if output_path else Pytubefix_Single.generate_output_path(file,nesting_level)
#         Pytubefix_Single.from_video_jsonlines(url,generated_output,source=source,from_date=from_date,to_date=to_date)
#         Pytubefix_Single.from_video_audio(url,generated_output,from_date=from_date,to_date=to_date,check_for_downloaded=check_for_downloaded)
#         print(f"Done processing single video: {url}\nOutput at: {generated_output}")
#         return generated_output
#     @staticmethod
#     def retry_failed_downloads(output_path,max_attempts=3,sleep_seconds=1):
#         output_path=Path(output_path); m4a_folder=output_path/'m4a_files'; failed_path=output_path/'not_downloaded.jl'
#         if not failed_path.exists():
#             print("No failed downloads to retry."); return
#         for attempt in range(1,max_attempts+1):
#             print(f"\n--- Attempt {attempt}/{max_attempts} ---")
#             failed_videos=[]
#             with jsonlines.open(failed_path,mode='r') as reader:
#                 for item in reader:
#                     try:
#                         title,video_id,_=item["error"]; retries=item.get("retries",0); failed_videos.append((title,video_id,item,retries))
#                     except Exception as parse_error:
#                         print(f"Skipping malformed line: {item} — {parse_error}")
#             if not failed_videos:
#                 print("Nothing to retry — all videos downloaded."); failed_path.unlink(); break
#             still_failed=[]
#             for idx,(title,video_id,item,retries) in enumerate(failed_videos,start=1):
#                 file_name=f"{video_id}.m4a"; fpath=m4a_folder/file_name
#                 if fpath.exists():
#                     print(f"[{idx}] Already downloaded: {title}"); continue
#                 try:
#                     yt=YouTube(f"https://www.youtube.com/watch?v={video_id}",use_oauth=True,allow_oauth_cache=True)
#                     stream=yt.streams.filter(only_audio=True).first()
#                     if stream is None: raise ValueError("No audio stream available.")
#                     stream.download(output_path=m4a_folder,filename=file_name)
#                     print(f"[{idx}] Successfully downloaded: {title}")
#                 except Exception as e:
#                     print(f"[{idx}] Still failed: {title} — {e}")
#                     ordered={"error":item["error"],"retries":retries+1}
#                     for key in sorted(item.keys()):
#                         if key.startswith("retry_error_"): ordered[key]=item[key]
#                     ordered[f"retry_error_{retries}"]=str(e)
#                     still_failed.append(ordered)
#                 time.sleep(sleep_seconds)
#             if still_failed:
#                 with jsonlines.open(failed_path,mode='w') as writer: writer.write_all(still_failed)
#                 print(f"{len(still_failed)} videos still failed. Will retry next round...")
#             else:
#                 print("🎉 All failed downloads recovered!"); failed_path.unlink(); break


# pytubefix_functions_single.py
# version: 2025-10-15b
from pytubefix import YouTube
from pytubefix import exceptions as ptfx_exc
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import dateparser, json, jsonlines, re, os, time

class Pytubefix_Single:
    @staticmethod
    def parse_partial_date(date_str):
        parsed=dateparser.parse(date_str,settings={'PREFER_DAY_OF_MONTH':'first','PREFER_DATES_FROM':'past'})
        if not parsed: raise ValueError(f"Invalid date input: '{date_str}'")
        return parsed.date()
    @staticmethod
    def extract_source(url):
        m=re.search(r'@([^/]+)',url)
        return m.group(1) if m else 'Unknown'
    @staticmethod
    def generate_output_path(file,nesting_level=4):
        script_path=Path(file).resolve()
        country=script_path.parents[nesting_level-3].name
        script_name=script_path.stem
        output_path=script_path.parents[nesting_level]/'data'/country/script_name
        print(f'This is the generated output path: {output_path}')
        return output_path
    @staticmethod
    def _normalize_yt_url(url:str)->str:
        u=unquote(url.strip()); p=urlparse(u); host=(p.netloc or "").lower(); path=p.path or ""; q=parse_qs(p.query); vid=(q.get("v") or [""])[0]
        if "watch" in path and vid: return f"https://www.youtube.com/watch?v={vid}"
        if "youtu.be" in host:
            vid=path.lstrip("/").split("/")[0]
            if vid: return f"https://www.youtube.com/watch?v={vid}"
        if "/embed/" in path:
            vid=path.split("/embed/")[-1].split("/")[0].split("?")[0].split("&")[0]
            if vid: return f"https://www.youtube.com/watch?v={vid}"
        if vid: return f"https://www.youtube.com/watch?v={vid}"
        return u
    @staticmethod
    def _extract_video_id(url:str)->str:
        try:
            p=urlparse(url); q=parse_qs(p.query); vid=(q.get("v") or [""])[0]
            if vid: return vid
            if "youtu.be" in (p.netloc or "").lower(): return (p.path or "").lstrip("/").split("/")[0]
            if "/embed/" in (p.path or ""): return p.path.split("/embed/")[-1].split("/")[0].split("?")[0].split("&")[0]
        except Exception: pass
        return ""
    # Replace _downloaded_ids with this
    @staticmethod
    def _downloaded_ids(m4a_folder:Path):
        try:
            return set(p.stem for p in m4a_folder.glob("*.m4a"))
        except Exception:
            return set()

        # In from_video_jsonlines, keep as-is except ensure we check file presence even if videos.jl lacks it:
        # ... after computing vid_hint and downloaded ...
        if vid_hint and vid_hint in downloaded:
            print(f"Already downloaded (by file), skipping metadata: {vid_hint}")
            return

    @staticmethod
    def _append_failure(failed_path:Path,title:str,video_id:str,err:str,url_for_log:str):
        try:
            seen=set()
            if failed_path.exists():
                with jsonlines.open(failed_path,mode='r') as r:
                    for item in r:
                        try:
                            _,v,_=item.get("error",["","",""]); u=item.get("url","")
                            if v: seen.add(f"VID::{v}")
                            if u: seen.add(f"URL::{u}")
                        except Exception: pass
            key=f"VID::{video_id}" if video_id else f"URL::{url_for_log}"
            if key not in seen:
                with jsonlines.open(failed_path,mode='a') as w:
                    w.write({"error":[title,video_id,str(err)],"url":url_for_log,"retries":0})
        except Exception as e: print(f"Failed to log failure for {url_for_log}: {e}")
    @staticmethod
    def _build_yt(url:str,prefer_android=False):
        kwargs=dict(use_oauth=True,allow_oauth_cache=True)
        if prefer_android:
            try: return YouTube(url,client="ANDROID",**kwargs)
            except TypeError: pass
            try: return YouTube(url,innertube_client="ANDROID",**kwargs)
            except TypeError: pass
        return YouTube(url,**kwargs)
    @staticmethod
    def _try_download_audio(yt,vid,fpath,m4a_folder,attempts=3):
        last_exc=None
        for i in range(attempts):
            try:
                stream=yt.streams.filter(only_audio=True).first()
                if stream is None: raise ValueError("No audio stream available.")
                stream.download(output_path=m4a_folder,filename=f"{vid}.m4a")
                return True,None
            except Exception as e:
                last_exc=e
                time.sleep(0.8*(i+1))
        return False,last_exc
    @staticmethod
    def from_video_jsonlines(url:str,output_path:Path,source:str='',from_date=None,to_date=None):
        url=Pytubefix_Single._normalize_yt_url(url)
        output_path=Path(output_path); output_path.mkdir(parents=True,exist_ok=True)
        jsonlines_path=output_path/'videos.jl'; failed_path=output_path/'not_downloaded.jl'; m4a_folder=output_path/'m4a_files'
        m4a_folder.mkdir(parents=True,exist_ok=True)
        downloaded=Pytubefix_Single._downloaded_ids(m4a_folder)
        if not source: source=Pytubefix_Single.extract_source(url)
        timestamp=datetime.now().strftime('%Y-%m-%d')
        existing=set()
        if jsonlines_path.exists():
            with jsonlines_path.open('r',encoding='utf-8') as f:
                for line in f:
                    try: existing.add(json.loads(line)['video_link'])
                    except Exception: pass
        vid_hint=Pytubefix_Single._extract_video_id(url)
        if vid_hint and vid_hint in downloaded:
            print(f"Already downloaded (by file), skipping metadata: {vid_hint}")
            return
        try:
            yt=Pytubefix_Single._build_yt(url,prefer_android=False)
        except Exception as e_ctor:
            if vid_hint in downloaded: return
            print(f"Skipping (cannot construct YouTube): {url} — {e_ctor}")
            Pytubefix_Single._append_failure(failed_path,"(unknown title)",vid_hint,f"CTOR:{e_ctor}",url); return
        if getattr(yt,"watch_url",url) in existing:
            print(f"Already in videos.jl, skipping metadata: {getattr(yt,'watch_url',url)}"); return
        try:
            yt.check_availability()
        except ptfx_exc.VideoPrivate as e_av:
            if getattr(yt,"video_id","") in downloaded or vid_hint in downloaded: return
            print(f"Skipping (private): {url} — {e_av}")
            Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or vid_hint,f"AVAIL_PRIVATE:{e_av}",url); return
        except ptfx_exc.VideoUnavailable as e_av:
            # Do NOT log yet; metadata may still be retrievable later, and audio may download; just continue.
            print(f"[warn] Availability said 'unavailable' for metadata: {url} — {e_av}")
        except Exception as e_avx:
            print(f"[warn] Unexpected availability during metadata: {url} — {type(e_avx).__name__}: {e_avx}")
        try:
            pub_date_write=""
            if getattr(yt,"publish_date",None):
                pdate=yt.publish_date.date()
                if from_date and pdate<from_date: print("Older than from_date — skipping metadata."); return
                if to_date and pdate>to_date: print("Newer than to_date — skipping metadata."); return
                pub_date_write=yt.publish_date.isoformat()
            try: title=yt.title
            except Exception: title="(unknown title)"
            data={'scrape_date':timestamp,'video_title':title,'source':source,'publication_date':pub_date_write,'video_link':getattr(yt,'watch_url',url),'video_id':getattr(yt,'video_id',vid_hint)}
            with jsonlines.open(jsonlines_path,mode='a') as w: w.write_all([data])
            print(f"💾 Wrote metadata: {title}")
        except Exception as e_meta:
            if getattr(yt,"video_id","") in downloaded or vid_hint in downloaded: return
            print(f"Failed metadata for {url}: {e_meta}")
            Pytubefix_Single._append_failure(failed_path,"(unknown title)",getattr(yt,"video_id","") or vid_hint,f"META:{e_meta}",url)
    # Replace from_video_audio with this (note: no blank lines inside the function)
    @staticmethod
    def from_video_audio(url:str,output_path:Path,from_date=None,to_date=None,check_for_downloaded=False):
        url=Pytubefix_Single._normalize_yt_url(url)
        output_path=Path(output_path); output_path.mkdir(parents=True,exist_ok=True)
        m4a_folder=output_path/'m4a_files'; m4a_folder.mkdir(parents=True,exist_ok=True)
        failed_path=output_path/'not_downloaded.jl'
        downloaded=Pytubefix_Single._downloaded_ids(m4a_folder)
        vid_hint=Pytubefix_Single._extract_video_id(url)
        if vid_hint:
            fpath=m4a_folder/f"{vid_hint}.m4a"
            if fpath.exists() or vid_hint in downloaded:
                print(f"Already downloaded, skipping audio: {vid_hint}.m4a")
                return
        last_exc=None
        for label,prefer_android in [("default",False),("android",True)]:
            try:
                yt=Pytubefix_Single._build_yt(url,prefer_android=prefer_android)
            except Exception as e_ctor:
                last_exc=e_ctor; continue
            try:
                vid=getattr(yt,"video_id",None) or vid_hint or ""
            except Exception:
                vid=vid_hint or ""
            if vid:
                fpath=m4a_folder/f"{vid}.m4a"
                if fpath.exists() or vid in downloaded:
                    print(f"Already downloaded, skipping audio: {vid}.m4a")
                    return
            try:
                yt.check_availability()
            except ptfx_exc.VideoPrivate as e_av:
                print(f"Skipping (private): {url} — {e_av}")
                if not (vid and (m4a_folder/f"{vid}.m4a").exists()):
                    Pytubefix_Single._append_failure(failed_path,"(unknown title)",vid or vid_hint,f"AVAIL_PRIVATE:{e_av}",url)
                return
            except ptfx_exc.VideoUnavailable as e_av:
                print(f"[{label}] Availability said 'unavailable' — will try download anyway: {url}")
            except Exception as e_avx:
                print(f"[{label}] Unexpected availability: {type(e_avx).__name__}: {e_avx} — will try download anyway")
            if getattr(yt,"publish_date",None):
                pdate=yt.publish_date.date()
                if from_date and pdate<from_date: print("Older than from_date — skipping audio."); return
                if to_date and pdate>to_date: print("Newer than to_date — skipping audio."); return
            ok,err=Pytubefix_Single._try_download_audio(yt,vid or vid_hint,m4a_folder/f"{(vid or vid_hint)}.m4a",m4a_folder,attempts=3)
            if ok:
                try: title=yt.title
                except Exception: title="(unknown title)"
                print(f"✅ Downloaded audio: {title}")
                return
            else:
                print(f"[{label}] Download attempt failed for {url}: {err}")
                last_exc=err
                continue
        final_vid=vid_hint or ""
        if final_vid and (m4a_folder/f"{final_vid}.m4a").exists(): return
        Pytubefix_Single._append_failure(failed_path,"(unknown title)",final_vid,f"DOWNLOAD:{last_exc}",url)

    @staticmethod
    def pytubefix_from_video(url:str,file,nesting_level=4,source:str='',output_path=None,from_date=None,to_date=None,check_for_downloaded=False):
        generated_output=Path(output_path) if output_path else Pytubefix_Single.generate_output_path(file,nesting_level)
        Pytubefix_Single.from_video_jsonlines(url,generated_output,source=source,from_date=from_date,to_date=to_date)
        Pytubefix_Single.from_video_audio(url,generated_output,from_date=from_date,to_date=to_date,check_for_downloaded=check_for_downloaded)
        print(f"Done processing single video: {url}\nOutput at: {generated_output}")
        return generated_output
    @staticmethod
    def retry_failed_downloads(output_path,max_attempts=3,sleep_seconds=1):
        output_path=Path(output_path); m4a_folder=output_path/'m4a_files'; failed_path=output_path/'not_downloaded.jl'
        if not failed_path.exists():
            print("No failed downloads to retry."); return
        for attempt in range(1,max_attempts+1):
            print(f"\n--- Attempt {attempt}/{max_attempts} ---")
            failed_videos=[]
            with jsonlines.open(failed_path,mode='r') as reader:
                for item in reader:
                    try:
                        title,video_id,_=item["error"]; retries=item.get("retries",0); failed_videos.append((title,video_id,item,retries))
                    except Exception as parse_error:
                        print(f"Skipping malformed line: {item} — {parse_error}")
            if not failed_videos:
                print("Nothing to retry — all videos downloaded."); failed_path.unlink(); break
            still_failed=[]
            for idx,(title,video_id,item,retries) in enumerate(failed_videos,start=1):
                fpath=m4a_folder/f"{video_id}.m4a"
                if fpath.exists():
                    print(f"[{idx}] Already downloaded: {title}"); continue
                try:
                    yt=Pytubefix_Single._build_yt(f"https://www.youtube.com/watch?v={video_id}",prefer_android=False)
                    ok,err=Pytubefix_Single._try_download_audio(yt,video_id,fpath,m4a_folder,attempts=3)
                    if not ok:
                        yt_alt=Pytubefix_Single._build_yt(f"https://www.youtube.com/watch?v={video_id}",prefer_android=True)
                        ok,err=Pytubefix_Single._try_download_audio(yt_alt,video_id,fpath,m4a_folder,attempts=3)
                    if ok:
                        print(f"[{idx}] Successfully downloaded: {title}")
                    else:
                        print(f"[{idx}] Still failed: {title} — {err}")
                        ordered={"error":item["error"],"retries":retries+1}
                        for key in sorted(item.keys()):
                            if key.startswith("retry_error_"): ordered[key]=item[key]
                        ordered[f"retry_error_{retries}"]=str(err)
                        still_failed.append(ordered)
                except Exception as e:
                    print(f"[{idx}] Unexpected retry error: {e}")
                    ordered={"error":item["error"],"retries":retries+1}
                    for key in sorted(item.keys()):
                        if key.startswith("retry_error_"): ordered[key]=item[key]
                    ordered[f"retry_error_{retries}"]=str(e)
                    still_failed.append(ordered)
                time.sleep(sleep_seconds)
            if still_failed:
                with jsonlines.open(failed_path,mode='w') as writer: writer.write_all(still_failed)
                print(f"{len(still_failed)} videos still failed. Will retry next round...")
            else:
                print("🎉 All failed downloads recovered!"); failed_path.unlink(); break
