import { useMemo } from 'react';
import { Navigate, useParams, useSearchParams } from 'react-router-dom';

/** 旧专项专区 URL → 首页专项入口 */
export default function ChannelLegacyRedirect() {
  const { channelId } = useParams<{ channelId: string }>();
  const [searchParams] = useSearchParams();
  const scenario = searchParams.get('scenario');
  const qs = new URLSearchParams({ intake: 'special' });
  if (channelId) qs.set('channel', channelId);
  if (scenario) qs.set('scenario', scenario);
  return <Navigate to={`/?${qs.toString()}#intake-desk`} replace />;
}
