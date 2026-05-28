import { useCallback, useEffect, useRef, useState } from 'react';

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null;
  onerror: ((ev: { error: string }) => void) | null;
  onend: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition;
}

/** 合并当前识别会话的全部结果（含中间结果），避免逐段 append 造成重复。 */
function mergeSessionTranscript(results: SpeechRecognitionResultList): string {
  let transcript = '';
  for (let i = 0; i < results.length; i++) {
    transcript += results[i]?.[0]?.transcript ?? '';
  }
  return transcript;
}

export function useSpeechInput(onTranscript: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState('');
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const callbackRef = useRef(onTranscript);
  const prefixRef = useRef('');
  callbackRef.current = onTranscript;

  useEffect(() => {
    setSupported(!!getSpeechRecognitionCtor());
    return () => {
      recRef.current?.stop();
      recRef.current = null;
    };
  }, []);

  const stop = useCallback(() => {
    recRef.current?.stop();
    setListening(false);
  }, []);

  const start = useCallback((prefix = '') => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setError('当前浏览器暂不支持语音输入');
      return;
    }

    prefixRef.current = prefix;
    setError('');

    try {
      recRef.current?.stop();

      const rec = new Ctor();
      rec.lang = 'zh-CN';
      rec.continuous = true;
      rec.interimResults = true;
      rec.onresult = (ev) => {
        const session = mergeSessionTranscript(ev.results);
        const full = prefixRef.current ? `${prefixRef.current}${session}` : session;
        callbackRef.current(full);
      };
      rec.onerror = (ev) => {
        setError(ev.error === 'not-allowed' ? '请允许麦克风权限' : '语音识别失败');
        setListening(false);
      };
      rec.onend = () => {
        setListening(false);
        recRef.current = null;
      };

      recRef.current = rec;
      rec.start();
      setListening(true);
    } catch {
      setError('当前浏览器暂不支持语音输入');
    }
  }, []);

  const toggle = useCallback(
    (prefix = '') => {
      if (listening) stop();
      else start(prefix);
    },
    [listening, start, stop],
  );

  return { supported, listening, error, start, stop, toggle };
}
