import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@/test/test-utils';
import LimitationCalculator from '@/pages/tools/LimitationCalculator';

describe('LimitationCalculator', () => {
  it('renders the page header', () => {
    render(<LimitationCalculator />);
    expect(screen.getByText('时效/期限计算')).toBeInTheDocument();
    expect(screen.getByText(/根据事件时间、是否在职与中断情况/)).toBeInTheDocument();
  });

  it('renders dispute type select', () => {
    render(<LimitationCalculator />);
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });

  it('renders all dispute type options', () => {
    render(<LimitationCalculator />);
    expect(screen.getByText('违法解除/解除争议')).toBeInTheDocument();
    expect(screen.getByText('在职欠薪（劳动关系存续）')).toBeInTheDocument();
    expect(screen.getByText('离职后欠薪/工资争议')).toBeInTheDocument();
    expect(screen.getByText('加班费争议')).toBeInTheDocument();
    expect(screen.getByText('未签书面劳动合同/二倍工资')).toBeInTheDocument();
    expect(screen.getByText('其他劳动争议')).toBeInTheDocument();
  });

  it('renders event date input', () => {
    const { container } = render(<LimitationCalculator />);
    const dateInput = container.querySelector('input[type="date"]');
    expect(dateInput).toBeInTheDocument();
  });

  it('renders interruption checkbox', () => {
    render(<LimitationCalculator />);
    expect(screen.getByText(/存在时效中断/)).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('shows termination date field when wage_in_service and not still employed', () => {
    const { container } = render(<LimitationCalculator />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'wage_in_service' } });

    const stillEmployedCheckbox = screen.getByRole('checkbox', { name: /目前仍在职/ });
    fireEvent.click(stillEmployedCheckbox);

    const dateInputs = container.querySelectorAll('input[type="date"]');
    expect(dateInputs.length).toBeGreaterThanOrEqual(2);
  });

  it('shows interruption date field when interruption checkbox is checked', () => {
    const { container } = render(<LimitationCalculator />);

    const checkbox = screen.getByRole('checkbox', { name: /存在时效中断/ });
    fireEvent.click(checkbox);

    const dateInputs = container.querySelectorAll('input[type="date"]');
    expect(dateInputs.length).toBeGreaterThanOrEqual(2);
  });

  it('calculates deadline for illegal termination', () => {
    const { container } = render(<LimitationCalculator />);

    const dateInput = container.querySelector('input[type="date"]')!;
    fireEvent.change(dateInput, { target: { value: '2024-01-01' } });

    expect(screen.getByText('2025-01-01')).toBeInTheDocument();
    expect(screen.getByText(/建议最迟提交仲裁/)).toBeInTheDocument();
  });

  it('shows expired status when deadline has passed', () => {
    const { container } = render(<LimitationCalculator />);

    const dateInput = container.querySelector('input[type="date"]')!;
    fireEvent.change(dateInput, { target: { value: '2020-01-01' } });

    expect(screen.getByText('已过期')).toBeInTheDocument();
  });

  it('copies results to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    const { container } = render(<LimitationCalculator />);

    const dateInput = container.querySelector('input[type="date"]')!;
    fireEvent.change(dateInput, { target: { value: '2024-01-01' } });

    const copyButton = screen.getByRole('button', { name: /复制结果/i });
    fireEvent.click(copyButton);

    expect(writeText).toHaveBeenCalled();
  });

  it('shows tips for wage_in_service when still employed', () => {
    render(<LimitationCalculator />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'wage_in_service' } });

    expect(screen.getByText(/不受一年仲裁时效限制/)).toBeInTheDocument();
  });

  it('calculates for wage_in_service when no longer employed', () => {
    const { container } = render(<LimitationCalculator />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'wage_in_service' } });

    const stillEmployedCheckbox = screen.getByRole('checkbox', { name: /目前仍在职/ });
    fireEvent.click(stillEmployedCheckbox);

    const dateInputs = container.querySelectorAll('input[type="date"]');
    const terminationDateInput = dateInputs[1];
    fireEvent.change(terminationDateInput, { target: { value: '2024-06-01' } });

    expect(screen.getByText('2025-06-01')).toBeInTheDocument();
  });

  it('handles interruption date correctly', () => {
    const { container } = render(<LimitationCalculator />);

    const dateInputs = container.querySelectorAll('input[type="date"]');
    fireEvent.change(dateInputs[0], { target: { value: '2024-01-01' } });

    const checkbox = screen.getByRole('checkbox', { name: /存在时效中断/ });
    fireEvent.click(checkbox);

    const allDateInputs = container.querySelectorAll('input[type="date"]');
    const interruptionDateInput = allDateInputs[1];
    fireEvent.change(interruptionDateInput, { target: { value: '2024-06-01' } });

    expect(screen.getByText('2025-06-01')).toBeInTheDocument();
  });
});
