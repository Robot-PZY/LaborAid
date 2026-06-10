import React from 'react';
import { AlertCircle, CheckCircle2, Info } from 'lucide-react';

interface FillRateBannerProps {
  aiMetadata?: {
    generation_mode?: string;
    structured_debug?: {
      template_fill_rate?: number;
      template_filled?: string[];
      template_missing?: string[];
    };
  };
}

/**
 * 模板变量填充率提示横幅
 * 显示在文书预览页面顶部，提示用户哪些变量已填充、哪些待补充
 */
export const FillRateBanner: React.FC<FillRateBannerProps> = ({ aiMetadata }) => {
  if (!aiMetadata || aiMetadata.generation_mode !== 'structured') {
    return null;
  }

  const debug = aiMetadata.structured_debug;
  if (!debug || debug.template_fill_rate === undefined) {
    return null;
  }

  const fillRate = debug.template_fill_rate;
  const filledCount = debug.template_filled?.length || 0;
  const missingCount = debug.template_missing?.length || 0;
  const totalCount = filledCount + missingCount;

  // 根据填充率决定样式
  const getStyle = () => {
    if (fillRate >= 0.8) {
      return {
        bgColor: 'bg-emerald-500/10',
        borderColor: 'border-emerald-500/35',
        iconColor: 'text-emerald-600',
        textColor: 'text-emerald-700',
        icon: CheckCircle2,
      };
    } else if (fillRate >= 0.6) {
      return {
        bgColor: 'bg-amber-500/10',
        borderColor: 'border-amber-500/35',
        iconColor: 'text-amber-600',
        textColor: 'text-amber-700',
        icon: Info,
      };
    } else {
      return {
        bgColor: 'bg-orange-500/10',
        borderColor: 'border-orange-500/35',
        iconColor: 'text-orange-600',
        textColor: 'text-orange-700',
        icon: AlertCircle,
      };
    }
  };

  const style = getStyle();
  const IconComponent = style.icon;

  // 生成友好的变量名称映射
  const getVariableLabel = (varName: string): string => {
    const labels: Record<string, string> = {
      applicant_name: '申请人姓名',
      applicant_gender: '申请人性别',
      applicant_birthdate: '申请人出生日期',
      applicant_ethnicity: '申请人民族',
      applicant_id_number: '申请人身份证号',
      applicant_address: '申请人地址',
      applicant_phone: '申请人电话',
      respondent_name: '被申请人名称',
      respondent_address: '被申请人地址',
      respondent_legal_representative: '被申请人法定代表人',
      entry_date: '入职日期',
      contract_start_date: '合同开始日期',
      contract_end_date: '合同结束日期',
      dismissal_date: '解除劳动关系日期',
      monthly_salary: '月工资',
      unpaid_wages: '未支付工资',
      overtime_pay: '加班费',
      severance_pay: '经济补偿金',
      damages: '赔偿金',
      work_injury_level: '工伤等级',
      medical_treatment_fee: '医疗费',
      arbitration_commission: '仲裁委员会名称',
      dispute_details: '争议详情',
      legal_analysis_expansion: '法律分析',
    };
    return labels[varName] || varName;
  };

  return (
    <div className={`rounded-lg border ${style.borderColor} ${style.bgColor} p-3 mb-4`}>
      <div className="flex items-start gap-2">
        <IconComponent className={`h-4 w-4 shrink-0 ${style.iconColor} mt-0.5`} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium ${style.textColor}`}>
            模板填充率：{Math.round(fillRate * 100)}%（{filledCount}/{totalCount}）
          </p>
          {missingCount > 0 && (
            <p className="text-xs text-muted-foreground mt-1">
              以下信息待补充：
              {debug.template_missing?.slice(0, 5).map((v, i) => (
                <span key={v}>
                  {i > 0 && '、'}
                  <span className="font-medium">{getVariableLabel(v)}</span>
                </span>
              ))}
              {missingCount > 5 && ` 等${missingCount}项`}
            </p>
          )}
          {missingCount === 0 && (
            <p className="text-xs text-muted-foreground mt-1">
              所有模板变量已填充，请核对内容准确性。
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
