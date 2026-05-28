import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AxiosError } from 'axios';
import {
  Loader2,
  Mic,
  MicOff,
  ImagePlus,
  FileUp,
  Sparkles,
  X,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { intakeApi, type IntakeAnalyzeResult } from '@/lib/api/intake';
import {
  clearIntakeSession,
  hasActiveIntakePlan,
  hydrateIntakeSessionFromServer,
  loadIntakeSession,
  type IntakeSession,
} from '@/lib/intake-session';
import { resultToSession, sessionToAnalyzeResult } from '@/lib/intake-plan';
import { useSpeechInput } from '@/hooks/useSpeechInput';
import IntakePlanResult from '@/components/intake/IntakePlanResult';
import IntakeSampleCards from '@/components/intake/IntakeSampleCards';
import { Button, Surface, Badge } from '@/components/ui/primitives';
import { addToolHistory } from '@/lib/tool-history';

const MAX_ATTACHMENTS = 3;
const IMAGE_ACCEPT = 'image/png,image/jpeg,image/jpg,image/gif,image/webp,image/bmp,image/tiff';
const FILE_ACCEPT =
  '.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document';

function isImageFile(file: File) {
  return file.type.startsWith('image/') || /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i.test(file.name);
}

function isPdfFile(file: File) {
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
}

function isWordFile(file: File) {
  return (
    file.type === 'application/msword'
    || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    || /\.docx?$/i.test(file.name)
  );
}

function isDocumentFile(file: File) {
  return isPdfFile(file) || isWordFile(file);
}

interface IntakeDeskProps {
  onAnalyzed?: (session: IntakeSession) => void;
}

export default function IntakeDesk({ onAnalyzed }: IntakeDeskProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const imageRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IntakeAnalyzeResult | null>(null);
  const [error, setError] = useState('');

  const applySpeech = useCallback((full: string) => {
    setText(full);
  }, []);

  const { supported: speechOk, listening, error: speechError, toggle: toggleSpeech } =
    useSpeechInput(applySpeech);

  const addAttachments = (incoming: File[], kind: 'image' | 'file') => {
    const valid = incoming.filter((f) => (kind === 'image' ? isImageFile(f) : isDocumentFile(f)));
    if (valid.length < incoming.length) {
      setError(kind === 'image' ? '请上传图片文件' : '请上传 PDF 或 Word 文件');
    }
    if (valid.length === 0) return;

    let overLimit = false;
    setAttachments((prev) => {
      const merged = [...prev, ...valid];
      if (merged.length > MAX_ATTACHMENTS) overLimit = true;
      const next = merged.slice(0, MAX_ATTACHMENTS);
      previews.forEach((u) => URL.revokeObjectURL(u));
      setPreviews(next.filter(isImageFile).map((f) => URL.createObjectURL(f)));
      return next;
    });
    if (overLimit) {
      setError(`最多上传 ${MAX_ATTACHMENTS} 个文件`);
    } else if (valid.length === incoming.length) {
      setError('');
    }
  };

  const handleImages = (files: FileList | null) => {
    if (!files) return;
    addAttachments(Array.from(files), 'image');
  };

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    addAttachments(Array.from(files), 'file');
  };

  const removeAttachment = (idx: number) => {
    setAttachments((prev) => {
      const next = prev.filter((_, i) => i !== idx);
      previews.forEach((u) => URL.revokeObjectURL(u));
      setPreviews(next.filter(isImageFile).map((f) => URL.createObjectURL(f)));
      return next;
    });
  };

  const handleAnalyze = async () => {
    if (!text.trim() && attachments.length === 0) {
      setError('请先输入文字描述或上传图片、文件');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await intakeApi.analyze(text.trim(), attachments);
      setResult(data);
      addToolHistory({
        kind: 'intake',
        title: data.cause_label || '维权咨询',
        subtitle: data.summary.slice(0, 48) + (data.summary.length > 48 ? '…' : ''),
        route: '/',
        query: text.trim().slice(0, 120),
      });
      const session = resultToSession(
        data,
        [text.trim(), data.extracted_from_images].filter(Boolean).join('\n\n'),
      );
      onAnalyzed?.(session);
    } catch (err: unknown) {
      const detail =
        err instanceof AxiosError ? err.response?.data?.detail || err.response?.data?.message : null;
      setError(typeof detail === 'string' ? detail : '分析失败，请稍后重试或检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  const restoreFromSession = useCallback(() => {
    const saved = loadIntakeSession();
    if (!saved?.actionPlan?.steps?.length && !saved?.recommendedTools?.length) return false;
    setResult(sessionToAnalyzeResult(saved));
    setText(saved.inputText || saved.caseFacts || '');
    setError('');
    return true;
  }, []);

  useEffect(() => {
    if (searchParams.get('resumeIntake') === '1') {
      restoreFromSession();
      const next = new URLSearchParams(searchParams);
      next.delete('resumeIntake');
      setSearchParams(next, { replace: true });
      requestAnimationFrame(() => {
        document.getElementById('intake-desk')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  }, [searchParams, setSearchParams, restoreFromSession]);

  useEffect(() => {
    hydrateIntakeSessionFromServer().then((saved) => {
      if (saved && hasActiveIntakePlan(saved) && !result) {
        setResult(sessionToAnalyzeResult(saved));
        setText(saved.inputText || saved.caseFacts || '');
      }
    });
  }, []);

  const handleReset = () => {
    setResult(null);
    setError('');
    setText('');
    clearIntakeSession();
  };

  return (
    <div id="intake-desk" className="scroll-mt-24">
    <Surface
      padding="lg"
      className="border-accent/20 bg-gradient-to-br from-card to-accent/5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Badge tone="accent">快速咨询</Badge>
          <h2 className="mt-2 font-display text-lg font-semibold">说说你的情况</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            说说情况后，将为您整理<strong className="font-medium text-foreground">分步维权安排</strong>
            ，并引导至相应功能页面
          </p>
        </div>
      </div>

      {!result ? (
        <div className="mt-4 space-y-3">
          {hasActiveIntakePlan() && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-accent/30 bg-accent/5 px-3 py-2.5">
              <p className="text-sm text-foreground">
                您有进行中的维权方案
                <span className="ml-1 text-muted-foreground">
                  （{loadIntakeSession()?.causeLabel}）
                </span>
              </p>
              <Button type="button" size="sm" variant="secondary" onClick={restoreFromSession}>
                继续查看方案
              </Button>
            </div>
          )}
          <IntakeSampleCards onPick={setText} disabled={loading} />

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            placeholder="例如：我是农民工，在工地干活，包工头欠我3个月工资约2.4万，仍在职；我有微信催款记录、工资条照片、考勤截图，想知道先投诉监察还是直接仲裁，以及该准备哪些文书。"
            className="w-full resize-none rounded-[var(--radius-md)] border border-border bg-background px-3 py-2.5 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
          />
          <p className="text-xs text-muted-foreground">
            可输入更完整经过（时间、金额、证据、目标诉求），系统会自动判断建议生成单份或批量文书。
          </p>

          <div className="flex flex-wrap items-center gap-2">
            {speechOk && (
              <Button
                type="button"
                variant={listening ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => toggleSpeech(listening ? '' : text)}
              >
                {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                {listening ? '停止录音' : '语音输入'}
              </Button>
            )}
            <Button type="button" variant="outline" size="sm" onClick={() => imageRef.current?.click()}>
              <ImagePlus className="h-4 w-4" />
              上传图片
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              <FileUp className="h-4 w-4" />
              上传文件
            </Button>
            <input
              ref={imageRef}
              type="file"
              accept={IMAGE_ACCEPT}
              multiple
              className="hidden"
              onChange={(e) => {
                handleImages(e.target.files);
                e.target.value = '';
              }}
            />
            <input
              ref={fileRef}
              type="file"
              accept={FILE_ACCEPT}
              multiple
              className="hidden"
              onChange={(e) => {
                handleFiles(e.target.files);
                e.target.value = '';
              }}
            />
            {attachments.length > 0 && (
              <span className="text-xs text-muted-foreground">
                已选 {attachments.length}/{MAX_ATTACHMENTS}
              </span>
            )}
          </div>

          {(speechError || error) && (
            <p className="flex items-center gap-1.5 text-sm text-amber-800 dark:text-amber-200">
              <AlertCircle className="h-4 w-4" />
              {speechError || error}
            </p>
          )}

          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {attachments.map((file, i) =>
                isImageFile(file) ? (
                  <div key={`${file.name}-${i}`} className="relative h-16 w-16 overflow-hidden rounded-md border">
                    <img
                      src={previews[attachments.slice(0, i).filter(isImageFile).length]}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      className="absolute right-0 top-0 bg-black/50 p-0.5 text-white"
                      onClick={() => removeAttachment(i)}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <div
                    key={`${file.name}-${i}`}
                    className="relative flex max-w-[140px] items-center gap-1.5 rounded-md border bg-muted/30 px-2 py-1.5 pr-6 text-xs"
                  >
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="truncate" title={file.name}>
                      {file.name}
                    </span>
                    <button
                      type="button"
                      className="absolute right-0.5 top-0.5 rounded p-0.5 text-muted-foreground hover:text-foreground"
                      onClick={() => removeAttachment(i)}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ),
              )}
            </div>
          )}

          <Button type="button" onClick={handleAnalyze} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {loading ? '分析中…' : '开始分析'}
          </Button>
        </div>
      ) : (
        <IntakePlanResult result={result} inputText={text} onReset={handleReset} />
      )}
    </Surface>
    </div>
  );
}
