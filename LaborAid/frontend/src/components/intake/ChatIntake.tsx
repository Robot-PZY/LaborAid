/**
 * ChatIntake - 简化版 intake
 * 两步选择身份 + 纠纷类型 → 弹出结构化表单
 * 选"其他"时走 AI 对话收集案情（支持多轮追问）
 */

import { useState, useRef, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Loader2, ArrowLeft, Bot, CheckCircle2, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getChannel } from '@/lib/channels';
import { listIntakeScenarios, findBestScenarioForCause } from '@/lib/intake-scenarios';
import { intakeApi, type IntakeAnalyzeResult } from '@/lib/api/intake';
import { loadIntakeSession, clearIntakeSession } from '@/lib/intake-session';
import ChannelIntakeWizard from './ChannelIntakeWizard';
import AnalysisResultCard from './AnalysisResultCard';
import { Button } from '@/components/ui/primitives';

interface ChatIntakeProps {
  className?: string;
  onComplete?: (caseId: number) => void;
}

const IDENTITY_OPTIONS = [
  { id: 'migrant-worker', label: '农民工', icon: '🏗️' },
  { id: 'intern-probation', label: '试用期员工', icon: '🎓' },
  { id: 'female-worker', label: '女职工', icon: '👩' },
  { id: 'gig-worker', label: '新就业形态', icon: '🛵' },
  { id: 'labor-dispatch', label: '劳务派遣', icon: '📦' },
  { id: 'other', label: '其他', icon: '🤷' },
];

const DISPUTE_OPTIONS = [
  { id: 'wage_arrears', label: '欠薪/拖欠工资', icon: '💰' },
  { id: 'illegal_termination', label: '被辞退/违法解除', icon: '🚫' },
  { id: 'overtime_pay', label: '加班费争议', icon: '⏰' },
  { id: 'no_written_contract', label: '没签劳动合同', icon: '📄' },
  { id: 'work_injury', label: '工伤赔偿', icon: '🏥' },
  { id: 'other', label: '其他', icon: '❓' },
];

// AI 头像组件
function AIAvatar({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const sizeClass = size === 'sm' ? 'h-6 w-6' : 'h-8 w-8';
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4';
  return (
    <div className={`${sizeClass} rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0`}>
      <Bot className={`${iconSize} text-white`} />
    </div>
  );
}

// 步骤指示器组件
function StepIndicator({ currentStage }: { currentStage: 'identity' | 'dispute' | 'form' }) {
  const steps = [
    { id: 'identity', label: '选择身份' },
    { id: 'dispute', label: '选择纠纷类型' },
    { id: 'form', label: '填写详情' },
  ];
  
  const getStageIndex = (stage: string) => {
    if (stage === 'identity') return 0;
    if (stage === 'dispute') return 1;
    return 2;
  };
  
  const currentIndex = getStageIndex(currentStage);
  
  return (
    <div className="flex items-center gap-2 mb-6">
      {steps.map((step, idx) => {
        const isCompleted = idx < currentIndex;
        const isCurrent = idx === currentIndex;
        return (
          <Fragment key={step.id}>
            <span
              className={cn(
                'h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold',
                isCompleted || isCurrent
                  ? 'bg-accent text-accent-foreground'
                  : 'bg-muted text-muted-foreground'
              )}
            >
              {isCompleted ? '✓' : idx + 1}
            </span>
            <span className={cn('text-sm', isCurrent ? 'font-medium text-foreground' : 'text-muted-foreground')}>
              {step.label}
            </span>
            {idx < steps.length - 1 && <span className="flex-1 h-px bg-border/60 mx-2" />}
          </Fragment>
        );
      })}
    </div>
  );
}

type Stage = 'identity' | 'dispute' | 'form' | 'chat';

interface ChatMsg {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  analysisResult?: IntakeAnalyzeResult;
}

export function ChatIntake({ className, onComplete }: ChatIntakeProps) {
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>('identity');
  const [channelId, setChannelId] = useState<string>('');
  const [scenarioId, setScenarioId] = useState<string>('');

  // AI 对话状态
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleStartNewCase = () => {
    clearIntakeSession();
    setStage('identity');
    setChannelId('');
    setScenarioId('');
    setChatMessages([]);
  };

  const handleIdentitySelect = (id: string) => {
    if (id === 'other') {
      setStage('chat');
      setChatMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: '你好！我是劳权智助的维权顾问。请简单描述一下你遇到的情况，比如：\n\n• 你是谁？（农民工、试用期员工等）\n• 遇到了什么问题？（欠薪、被辞退等）\n• 涉及哪些公司或单位？\n\n我会帮你分析并生成维权方案。',
        },
      ]);
      return;
    }
    setChannelId(id);
    setStage('dispute');
  };

  const handleDisputeSelect = (disputeId: string) => {
    const channel = getChannel(channelId);
    if (channel) {
      const scenarios = listIntakeScenarios(channel);
      const matched = findBestScenarioForCause(channelId, disputeId, scenarios);
      if (matched) {
        setScenarioId(matched.id);
        setStage('form');
      } else {
        // 无匹配场景，提示用户并返回
        alert('当前身份下暂无对应的纠纷类型表单，请尝试其他身份或使用"其他"身份进行 AI 对话。');
        // 不跳转，保持在 dispute 阶段
      }
    } else {
      alert('未找到对应的身份信息，请重新选择。');
      setStage('identity');
      setChannelId('');
    }
  };

  // AI 对话发送
  const handleChatSend = async () => {
    const text = chatInput.trim();
    if (!text || chatLoading) return;

    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: 'user', content: text };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      // 拼接历史对话作为上下文
      const historyText = chatMessages
        .filter((m) => m.role === 'user')
        .map((m) => m.content)
        .join('\n');
      const fullText = historyText ? `${historyText}\n${text}` : text;

      // 使用项目 API 客户端
      const result = await intakeApi.analyze(fullText);

      // 结构化卡片回复
      const replyText = buildChatReply(result);
      setChatMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: 'assistant', content: replyText, analysisResult: result },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { id: `e-${Date.now()}`, role: 'assistant', content: '抱歉，分析时出现了问题，请重试。' },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleBack = () => {
    if (stage === 'dispute') {
      setStage('identity');
      setChannelId('');
    } else if (stage === 'form') {
      setStage('dispute');
      setScenarioId('');
    } else if (stage === 'chat') {
      setStage('identity');
      setChatMessages([]);
    }
  };

  const handleCaseCreated = (caseId: number) => {
    onComplete?.(caseId);
  };

  // 表单阶段
  if (stage === 'form') {
    return (
      <div className={cn('bg-background rounded-lg border border-border/70 p-6', className)}>
        <ChannelIntakeWizard
          onBack={handleBack}
          initialChannelId={channelId}
          initialScenarioId={scenarioId}
          onCaseCreated={handleCaseCreated}
        />
      </div>
    );
  }

  // AI 对话阶段
  if (stage === 'chat') {
    return (
      <div className={cn('flex flex-col h-[600px] bg-background rounded-lg border border-border/70', className)}>
        {/* 标题栏 */}
        <div className="px-6 pt-4 pb-2 border-b border-border/40">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={handleBack}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <AIAvatar />
            <div>
              <h3 className="font-semibold text-sm">AI 维权顾问</h3>
              <p className="text-xs text-muted-foreground">描述您的情况，获取维权方案</p>
            </div>
          </div>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {chatMessages.map((msg) => (
            <div key={msg.id} className={cn('flex gap-3', msg.role === 'user' ? 'flex-row-reverse' : 'flex-row')}>
              {msg.role === 'user' ? (
                <div className="h-8 w-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center text-sm font-medium flex-shrink-0">
                  我
                </div>
              ) : (
                <AIAvatar />
              )}
              <div className={cn('max-w-[80%] space-y-2', msg.role === 'user' ? 'items-end' : 'items-start')}>
                {/* 文本内容 */}
                {msg.content && (
                  <div
                    className={cn(
                      'rounded-lg px-4 py-2 text-sm whitespace-pre-wrap',
                      msg.role === 'user' ? 'bg-accent text-accent-foreground' : 'bg-muted'
                    )}
                  >
                    {msg.content}
                  </div>
                )}
                {/* 结构化分析卡片 */}
                {msg.analysisResult && <AnalysisResultCard result={msg.analysisResult} />}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex items-center gap-2 ml-11">
              <Loader2 className="h-4 w-4 animate-spin text-accent" />
              <span className="text-sm text-muted-foreground">正在分析...</span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="px-6 py-4 border-t border-border/60">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleChatSend();
                }
              }}
              placeholder="继续描述您的情况，或追问更多细节..."
              className="flex-1 px-3 py-2 border border-border/70 rounded-md focus:outline-none focus:ring-2 focus:ring-accent/40 bg-background text-foreground text-sm"
              disabled={chatLoading}
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleChatSend}
              disabled={chatLoading || !chatInput.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            分析完成后可继续补充信息，或前往
            <button
              type="button"
              className="text-accent underline mx-1"
              onClick={() => setStage('identity')}
            >
              专项通道
            </button>
            填写详细表单
          </p>
        </div>
      </div>
    );
  }

  // 纠纷类型选择阶段
  if (stage === 'dispute') {
    const selectedIdentity = IDENTITY_OPTIONS.find((opt) => opt.id === channelId);
    return (
      <div className={cn('bg-background rounded-lg border border-border/70 p-6', className)}>
        <StepIndicator currentStage="dispute" />

        <div className="flex items-center gap-2 mb-4">
          <Button variant="ghost" size="sm" onClick={() => { setStage('identity'); setChannelId(''); }}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            重选身份
          </Button>
          {selectedIdentity && (
            <span className="text-sm text-muted-foreground">
              已选择：<span className="font-medium text-foreground">{selectedIdentity.icon} {selectedIdentity.label}</span>
            </span>
          )}
        </div>

        <h3 className="text-lg font-semibold mb-1">你遇到了什么问题？</h3>
        <p className="text-sm text-muted-foreground mb-4">选择最符合你情况的纠纷类型</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {DISPUTE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => handleDisputeSelect(opt.id)}
              className="relative z-10 p-4 rounded-lg border border-border/60 bg-card text-center transition-all hover:border-accent/40 hover:bg-accent/5 hover:shadow-sm cursor-pointer"
            >
              <span className="text-3xl block mb-2">{opt.icon}</span>
              <span className="text-sm font-medium">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // 已有活跃案件 - 显示提示
  const existingSession = loadIntakeSession();
  if (existingSession?.createdCaseId && stage === 'identity') {
    return (
      <div className={cn('bg-background rounded-lg border border-border/70 p-6', className)}>
        <div className="text-center space-y-4 py-6">
          <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
          <div>
            <h3 className="text-lg font-semibold mb-1">您已有进行中的案件</h3>
            <p className="text-sm text-muted-foreground">
              案件 #{existingSession.createdCaseId} 正在处理中，请先完成当前案件或开始新案件。
            </p>
          </div>
          <div className="flex gap-3 justify-center">
            <Button
              variant="primary"
              onClick={() => navigate(`/cases/${existingSession.createdCaseId}`)}
            >
              查看案件
            </Button>
            <Button
              variant="outline"
              onClick={handleStartNewCase}
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              开始新案件
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // 身份选择阶段
  return (
    <div className={cn('bg-background rounded-lg border border-border/70 p-6', className)}>
      <StepIndicator currentStage="identity" />

      <h3 className="text-lg font-semibold mb-1">请问你的身份是？</h3>
      <p className="text-sm text-muted-foreground mb-4">选择最符合你情况的身份类型</p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {IDENTITY_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => handleIdentitySelect(opt.id)}
            className="relative z-10 p-4 rounded-lg border border-border/60 bg-card text-center transition-all hover:border-accent/40 hover:bg-accent/5 hover:shadow-sm cursor-pointer"
          >
            <span className="text-3xl block mb-2">{opt.icon}</span>
            <span className="text-sm font-medium">{opt.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/** 根据分析结果生成对话式引导文本 */
function buildChatReply(result: IntakeAnalyzeResult): string {
  const parts: string[] = [];
  parts.push(`根据你的描述，我初步判断这属于「${result.cause_label}」类型的纠纷。`);

  if (result.action_plan?.steps?.length) {
    parts.push(`\n🎯 建议的维权步骤：`);
    result.action_plan.steps.slice(0, 3).forEach((step) => {
      parts.push(`  ${step.step}. ${step.label}`);
    });
  }

  parts.push(`\n💡 详细分析见下方卡片，你可以继续补充更多信息。`);
  return parts.join('\n');
}
