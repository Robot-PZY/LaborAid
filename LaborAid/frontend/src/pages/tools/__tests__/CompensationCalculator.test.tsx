import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
import CompensationCalculator from '@/pages/tools/CompensationCalculator';

describe('CompensationCalculator', () => {
  it('renders the page header', () => {
    render(<CompensationCalculator />);
    expect(screen.getByText('赔偿/补偿计算')).toBeInTheDocument();
    expect(screen.getByText(/按月工资、工龄与解除类型/)).toBeInTheDocument();
  });

  it('renders termination type select', () => {
    const { container } = render(<CompensationCalculator />);
    const select = container.querySelector('select');
    expect(select).toBeInTheDocument();
  });

  it('renders all termination type options', () => {
    const { container } = render(<CompensationCalculator />);
    const options = container.querySelectorAll('option');
    expect(options).toHaveLength(6);
  });

  it('renders wage input field', () => {
    render(<CompensationCalculator />);
    expect(screen.getByPlaceholderText('例如：8000')).toBeInTheDocument();
  });

  it('renders years and months input fields', () => {
    const { container } = render(<CompensationCalculator />);
    const inputs = container.querySelectorAll('input');
    expect(inputs.length).toBeGreaterThanOrEqual(3);
  });

  it('renders cap checkbox', () => {
    render(<CompensationCalculator />);
    expect(screen.getByText(/启用 3 倍社平工资封顶提示/)).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('shows local average wage field when cap checkbox is checked', () => {
    render(<CompensationCalculator />);

    const checkbox = screen.getByRole('checkbox', { name: /启用 3 倍社平工资封顶提示/ });
    fireEvent.click(checkbox);

    expect(screen.getByPlaceholderText('例如：10000')).toBeInTheDocument();
  });

  it('calculates compensation for illegal termination', () => {
    const { container } = render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '10000' } });

    const inputs = container.querySelectorAll('input');
    fireEvent.change(inputs[1], { target: { value: '5' } });
    fireEvent.change(inputs[2], { target: { value: '0' } });

    expect(screen.getAllByText('¥100,000').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/赔偿金 = 2N × 月工资/)).toBeInTheDocument();
  });

  it('calculates N correctly with months', () => {
    const { container } = render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '8000' } });

    const inputs = container.querySelectorAll('input');
    fireEvent.change(inputs[1], { target: { value: '3' } });
    fireEvent.change(inputs[2], { target: { value: '3' } });

    expect(screen.getByText('3.5')).toBeInTheDocument();
    expect(screen.getByText('¥28,000')).toBeInTheDocument();
  });

  it('applies 3x cap when wage exceeds local average', () => {
    const { container } = render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '50000' } });

    const inputs = container.querySelectorAll('input');
    fireEvent.change(inputs[1], { target: { value: '5' } });

    const checkbox = screen.getByRole('checkbox', { name: /启用 3 倍社平工资封顶提示/ });
    fireEvent.click(checkbox);

    const localAvgInput = screen.getByPlaceholderText('例如：10000');
    fireEvent.change(localAvgInput, { target: { value: '10000' } });

    expect(screen.getByText(/你启用了"3 倍社平工资封顶"/)).toBeInTheDocument();
    expect(screen.getByText(/月工资按 30,000 元计/)).toBeInTheDocument();
  });

  it('calculates zero compensation for employee resignation', () => {
    const { container } = render(<CompensationCalculator />);

    const select = container.querySelector('select')!;
    fireEvent.change(select, { target: { value: 'employee_resign' } });

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '10000' } });

    const inputs = container.querySelectorAll('input');
    fireEvent.change(inputs[1], { target: { value: '5' } });

    expect(screen.getByText('¥0')).toBeInTheDocument();
    expect(screen.getByText(/通常：补偿为 0/)).toBeInTheDocument();
  });

  it('copies results to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '10000' } });

    const copyButton = screen.getByRole('button', { name: /复制结果/i });
    fireEvent.click(copyButton);

    expect(writeText).toHaveBeenCalled();
  });

  it('shows calculation details table', () => {
    render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '10000' } });

    const { container } = render(<CompensationCalculator />);
    const inputs = container.querySelectorAll('input');
    fireEvent.change(inputs[1], { target: { value: '5' } });

    expect(screen.getByText('计算明细')).toBeInTheDocument();
    expect(screen.getByText('经济补偿 (N)')).toBeInTheDocument();
    expect(screen.getByText('赔偿金 (2N)')).toBeInTheDocument();
    expect(screen.getByText(/代通知金（1个月）/)).toBeInTheDocument();
  });

  it('shows calculation basis section', () => {
    render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '10000' } });

    expect(screen.getByText('计算依据')).toBeInTheDocument();
  });

  it('shows warning when N exceeds 12 years', () => {
    const { container } = render(<CompensationCalculator />);

    const wageInput = screen.getByPlaceholderText('例如：8000');
    fireEvent.change(wageInput, { target: { value: '10000' } });

    const inputs = container.querySelectorAll('input');
    fireEvent.change(inputs[1], { target: { value: '15' } });

    expect(screen.getByText(/经济补偿年限在部分规则下可能存在上限/)).toBeInTheDocument();
  });
});
